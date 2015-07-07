#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file contains Web Application
"""
import os
import json
import time

import tornado.ioloop
import tornado.httpserver
import tornado.web
import tornado.websocket
from tornado.options import options, define
from tornado.options import parse_config_file, parse_command_line

import hwconf
import auth
import utils
import scpi2widgets
from decorators import api_auth

VERSION = "0.1"
LICENSE = "GPL v3.0"
PROJECT = "easy_phi"

# configuration defaults
define("conf_path", default="/etc/easy_phi.conf")
define("static_path",
       default=os.path.join(os.path.dirname(__file__), '..', 'static'))
define("server_port", default=8000)
define("hw_version", default='N/A')
define("vendor", type=str)
define("welcome_message", default="")

define("debug", default=False)

define("default_format", default='json')

#WebSocket object
global ws

class APIHandler(tornado.web.RequestHandler):
    """ Tornado handlers subclass to format response to xml/json/plain """

    def data_received(self, chunk):
        # to get rid of annoying pylint message about not implemented
        # abstract method
        pass

    def write(self, chunk):
        fmt = self.get_argument('format', options.default_format)
        if fmt not in ('xml', 'json', 'plain'):
            fmt = options.default_format
        chunk, ctype = utils.format_conversion(chunk, fmt, options.debug)
        if fmt == 'json':
            callback = self.get_argument('callback', '')
            if callback:  # JSONP support, for cross-domain static JS API
                chunk = ''.join((callback, '(', chunk, ')'))
        self.set_header('Content-Type', ctype)

        super(APIHandler, self).write(chunk)

    def get(self):
        self.set_status(405)
        self.write({'errror': "This method does not accept GET requests"})

    def post(self):
        self.set_status(405)
        self.write({'errror': "This method does not accept POST requests"})

    def put(self):
        self.set_status(405)
        self.write({'errror': "This method does not accept PUT requests"})

    def delete(self):
        self.set_status(405)
        self.write({'errror': "This method does not accept DELETE requests"})


class ModuleHandler(APIHandler):
    """ APIHandler subclass to handle slot number validation
    It is intended for handlers working with modules """
    allow_broadcast = False
    slot = None
    module = None  # updated by self.prepare() if slot number is correct
    api_token = None  # updated by decorator @api_auth

    def prepare(self):
        err = ''
        slot = self.get_argument('slot', '')
        if slot == '':
            err = 'Missing slot number. Add ?slot=N to URL'
        else:
            try:
                self.slot = int(slot)
            except ValueError:
                err = 'Slot number must be an integer'
            else:
                max_slot = len(hwconf.modules) - 1
                min_slot = 0 if self.allow_broadcast else 1
                if not min_slot <= self.slot <= max_slot:  # invalid slot number
                    err = 'Invalid slot number. Number in range ' + \
                          '{0}..{1} expected'.format(min_slot, max_slot)
                elif hwconf.modules[self.slot] is None:
                    err = 'Selected slot is empty'

        if err:
            self.set_status(400)
            self.finish({'error': err})
            return

        self.module = hwconf.modules[self.slot]


class PlatformInfoHandler(APIHandler):
    """ Return basic info about the system """
    def get(self):
        self.write({
            'sw_version': VERSION,
            'hw_version': options.hw_version,
            'vendor': options.vendor,
            'slots': len(options.ports),
            'supported_api_versions': [1],
            'welcome_message': options.welcome_message
        })


class ModuleInfoHandler(ModuleHandler):
    """ Return basic info about a module """
    allow_broadcast = True

    def get(self):
        device = self.module.device or {}
        self.write({
            'name': self.module.name,
            'sw_version': 'N/A',  # TODO: find out actual field
            'hw_version': device.get('ID_REVISION', 'N/A'),
            'vendor': device.get('ID_VENDOR', 'N/A'),
            'serial_no': device.get('ID_SERIAL_SHORT', 'N/A'),
        })


class ModulesListHandler(APIHandler):
    """ Return list of module names"""
    def get(self):
        self.write([module and module.name for module in hwconf.modules])


class ListSCPICommandsHandler(ModuleHandler):
    """List SCPI commands supported by the selected module. """
    allow_broadcast = True

    def get(self):
        self.write(self.module.get_configuration())


class SelectModuleHandler(ModuleHandler):
    """Select the module, identified by ID passed as a URL parameter.

    When user selects module in web interface, all other users should be
    be able to see this module is used by someone else.
    """
    allow_broadcast = False

    def post(self):
        """ Set user lock on module to indicate it is used by someone """
        used_by = getattr(self.module, 'used_by', None)
        if used_by is not None:
            self.set_status(400)
            return {'error': "Module is used by {0}. If you need this module, "
                             "you might force unlock it by issuing DELETE "
                             "request first.".format(used_by)}
        setattr(self.module, 'used_by', auth.user_by_token(self.api_token))
        self.write("OK")

    def delete(self):
        """ Force to remove any user lock from the module """
        used_by = getattr(self.module, 'used_by', None)
        if used_by is None:
            self.set_status(400)
            return {'error': 'Module is not used by anyone at the moment'}
        setattr(self.module, 'used_by', None)
        self.write("OK")

    def get(self):
        """ Return user lock status of the module
        :param: id: integer, slot number 1...N
        :return: user name of the person using this module, None otherwise
        """
        self.write(getattr(self.module, 'used_by', None))


class SCPICommandHandler(ModuleHandler):
    """API function to send SCPI command to module in the specified rack slot"""
    allow_broadcast = True

    def post(self):
        """Transfer SCPI command to a module and return the response"""
        # Check user lock status
        used_by = getattr(self.module, 'used_by', None)
        # auth.user_by_token(None) returns None, in case selection isn't used
        if used_by != auth.user_by_token(self.api_token):
            self.set_status(409)  # Conflict
            self.finish({
                'error': "Module is used by {0}. If you need this module, you "
                         "need force unlock it first.".format(used_by)
            })
            return

        scpi_command = self.request.body
        if not scpi_command:
            self.set_status(400)
            self.finish({'error': 'SCPI command expected in POST body'})
            return

        self.write(self.module.scpi(scpi_command))

class ModuleUIHandler(ModuleHandler):
    """API function to return small JS script to create module UI"""
    allow_broadcast = True

    def write(self, chunk):
        """This handler needs slot parameter but does not need formatting
        This method is restored to original tornado.web.RequestHandler.write()
        """
        return super(APIHandler, self).write(chunk)

    def get(self):
        container = self.get_argument('container', '')
        if not container:
            self.set_status(400)
            self.finish({'errror': "Missing container parameter, jQuery"
                         "of the DOM element to include module UI"})
            return

        supported_commands = self.module.get_configuration()
        widgets = scpi2widgets.scpi2widgets(supported_commands)

        self.set_header('Content-type', 'application/javascript')

        temp_id = int(time.time()*1000)
        for widget in widgets:
            temp_id += 1
            self.write("""$("{container}").append("<section id='{temp_id}' """
                       """class='widget'></section>");\n""".format(
                           container=container, temp_id=temp_id))
            # this wrapping into anonymous function is to not mess with global
            # variables. To isolate syntax errors, in future it is wrapped into
            # eval() statement.
            self.write(
                "(function(slot, container, scpi){{\n"
                "\teval({widget});\n"
                "}})({slot}, $('#{container_id}'), function(scpi, callback){{\n"
                "    ep.scpi({slot}, scpi, callback);\n}});\n".format(
                    widget=json.dumps(widget),
                    slot=self.slot,
                    container_id=temp_id
                )
            )

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def update_module(added, slot):
        global ws
        ws.write_message({
            'msg_type': 'MODULE_UPDATE',
            'slot': slot,
            'added': added
        })

    def open(self):
        global ws
        #Save WebSocket object
        ws = self
        #Add callback methods to hwconf module
        hwconf.callbacks.append(self.update_module)

    def close(self):
        #remove callbacks from hwconf module
        hwconf.callbacks.remove(self.update_module)

class AdminConsoleHandler(tornado.web.RequestHandler):
    """Placeholder for Admin Console web-page"""

    def get(self):
        self.write("Coming soon..")


class ContorlledCacheStaticFilesHandler(tornado.web.StaticFileHandler):
    """Debug handler to serve static files without caching"""

    def set_extra_headers(self, path):
        if options.debug:
            # parent method is empty, no need to call super
            self.set_header(
                'Cache-control', 'no-cache, no-store, must-revalidate')


class PageNotFoundHandler(tornado.web.RequestHandler):
    """Custom 404 page"""

    def get(self):
        self.set_status(404)
        # TODO: add nice template with clear message
        self.write("Page not found")

    post = put = delete = get


def main(application):
    # start hw configuration monitoring. It requires configuration of hw ports
    # so it shall be done after parsing conf file
    hwconf.start()

    # we need HTTP server to serve SSL requests.
    ssl_ctx = None
    http_server = tornado.httpserver.HTTPServer(
        application, ssl_options=ssl_ctx)
    http_server.listen(options.server_port)
    tornado.ioloop.IOLoop.current().start()

    # TODO: add TCP socket handler to listen for HiSlip requests from VISA

if __name__ == '__main__':
    # parse command line twice to allow pass configuration file path
    parse_command_line(final=False)
    parse_config_file(options.conf_path, final=False)
    # command-line args override conf file options
    parse_command_line()
else:
    try:
        parse_config_file(options.conf_path, final=False)
    except IOError:  # configuration file doesn't exist, use defaults
        pass

settings = {
    'debug': options.debug,
    'default_handler_class': PageNotFoundHandler,
}

# URL schemas to RequestHandler classes mapping
application = tornado.web.Application([
    (r"/", tornado.web.RedirectHandler,
        {"url": '/static/index.html'}),
    (r"/api/v1/info", PlatformInfoHandler),
    (r"/api/v1/module", ModuleInfoHandler),
    (r"/api/v1/modules_list", ModulesListHandler),
    (r"/api/v1/module_scpi_list", ListSCPICommandsHandler),
    (r"/api/v1/lock_module", SelectModuleHandler),
    (r"/api/v1/send_scpi", SCPICommandHandler),
    (r"/api/v1/module_ui_controls", ModuleUIHandler),
    (r"/admin", AdminConsoleHandler),
    (r"/websocket", WebSocketHandler),
    (r"/static/(.*)", ContorlledCacheStaticFilesHandler,
        {"path": options.static_path}),
], **settings)

if __name__ == '__main__':
    main(application)
