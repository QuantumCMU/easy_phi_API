#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file contains Web Application
"""
import os

import tornado.ioloop
import tornado.httpserver
import tornado.web
from tornado.options import options, define
from tornado.options import parse_config_file, parse_command_line

import hwconf
import auth
import utils
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

settings = {
    'debug': options.debug,
    'autoreload' : options.debug,
}

try:
    parse_config_file(options.conf_path, final=False)
except IOError:  # file might not exist by default path
    raise


class APIHandler(tornado.web.RequestHandler):
    """ Tornado handlers subclass to format response to xml/json/plain """

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
            'slots': len(hwconf.modules),
            'supported_api_versions': [1],
            'welcome_message': options.welcome_message
        })


        }


class ModulesListHandler(APIHandler):
    """ Return list of modules with their metadata and currnent status (locked/unlocked)"""
    def get(self):
        return [[None, None] if module is None
                else [module.name, getattr(module, 'used_by', None)]
                for module in hwconf.modules]


class SelectModuleHandler(ModuleHandler):
    """Select the module, identified by ID passed as a URL parameter.

    When user selects module in web interface, all other users should be
    be able to see this module is used by someone else.

    """
    allow_broadcast = False

    @api_auth
    def post(self):
        """ Set user lock on module to indicate it is used by someone """
        used_by = getattr(self.module, 'used_by', None)
        if used_by is not None:
            self.set_status(400)
            return {'error': 'Module is used by {0}. If you '.format(used_by) +
                             'need this module, you might force unlock it '
                             'by issuing DELETE request first.'}
        setattr(self.module, 'used_by', auth.user_by_token(self.api_token))
        self.write("OK")

    @api_auth
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
    """API functions related to a module in the specified rack slot"""
    allow_broadcast = True

    def post(self):
        """Transfer SCPI command to a module and return the response"""
        # Check user lock status
        used_by = getattr(self.module, 'used_by', None)
        # auth.user_by_token(None) returns None, in case selection isn't used
        if used_by != auth.user_by_token(self.api_token):
            self.set_status(409)  # Conflict
            self.finish({
                'error': 'Module is used by {0}. If you '.format(used_by) +
                         'need this module, you might force unlock it first.'
            })
            return

        scpi_command = self.request.body
        if not scpi_command:
            self.set_status(400)
            self.finish({'error': 'SCPI command expected in POST body'})
            return

        self.write(self.module.scpi(scpi_command))


class AdminConsoleHandler(tornado.web.RequestHandler):
    """Placeholder for Admin Console web-page"""

    def get(self):
        self.write("Coming soon..")

# URL schemas to RequestHandler classes mapping
application = tornado.web.Application([
    (r"/", tornado.web.RedirectHandler,
        {"url": '/static/index.html'}),
    (r"/api/v1/info", PlatformInfoHandler),
    (r"/api/v1/modules_list", ModulesListHandler),
    (r"/api/v1/module/select", SelectModuleHandler),
    (r"/api/v1/module", SCPICommandHandler),
    (r"/admin", AdminConsoleHandler),
    (r"/static/(.*)", tornado.web.StaticFileHandler,
        {"path": options.static_path}),
], **settings)

if __name__ == '__main__':
    parse_config_file(options.conf_path, final=False)
    parse_command_line()  # command-line args override conf file options

    # start hw configuration monitoring. It requires configuration of hw ports
    # so it shall be done after parsing conf file
    hwconf.start()

    # we need HTTP server to serve SSL requests.
    ssl_ctx = None
    http_server = tornado.httpserver.HTTPServer(application, ssl_options=ssl_ctx)
    http_server.listen(options.server_port)
    tornado.ioloop.IOLoop.current().start()

    # TODO: add TCP socket handler to listen for HiSlip requests from VISA
