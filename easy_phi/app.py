#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file contains Web Application
"""
import os
import json
import time
import pip

import tornado.ioloop
import tornado.httpserver
import tornado.web
import tornado.websocket
import tornado.gen

from tornado.options import options, define
from tornado.options import parse_config_file, parse_command_line

from easy_phi import hwconf
from easy_phi import auth
from easy_phi import utils
from easy_phi import scpi2widgets

# whenever you change version, please update setup.py as well
from easy_phi import __version__, __project__

# configuration defaults
define("conf_path", default="/etc/easy_phi.conf")
define("template_path",
       default=os.path.join(os.path.dirname(__file__), 'templates'))
define("static_path", default=os.path.join(os.path.dirname(__file__), 'static'))
define("server_port", default=8000)
define("sw_version", default=__version__)
define("hw_version", default='N/A')
define("vendor", type=str)
define("welcome_message", default="")

define("debug", default=False)

define("default_format", default='json')

# WebSocket object
ws = None


class APIHandler(tornado.web.RequestHandler):
    """ Tornado handlers subclass to format response to xml/json/plain """

    # default value of api_token is empty string
    # this is done to make it optional with dummy auth backend
    api_token = None

    def prepare(self):
        """ Look for API token in request
        API token is looked in following order:
            - session cookie (to support access from web interface)
            - HTTP Basic auth password, if username is api_token
            - GET request variable api_token
        """
        api_token = self.get_cookie(options.session_cookie_name)

        if api_token is None:
            user, pwd = auth.parse_http_basic_auth(self.request)
            if user == 'api_token':
                api_token = pwd

        if api_token is None:
            api_token = self.get_argument('api_token', '')

        if not auth.validate_api_token(api_token):
            self.set_status(401)
            self.finish({"error": "api_token is missing or invalid. You can "
                                  "pass api token in request GET parameters, "
                                  "cookie or HTTP. To get api token please "
                                  "login and check api token in your profile"
                         })
            return

        self.api_token = api_token

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
        """ It is totally possible to use SUPPORTED_METHODS to return HTTP 405
        We use explicit methods definitions because it is easier to subclass.

        Also, we don't use HTTPError exception to format response by write()
        """
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

    def prepare(self):
        super(ModuleHandler, self).prepare()

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
            'sw_version': options.sw_version,
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
        if used_by == auth.user_by_token(self.api_token):
            self.finish("OK")
            return
        if used_by is not None:
            self.set_status(400)
            self.finish({'error': "Module is used by {0}. If you need this "
                                 "module, you might force unlock it by issuing "
                                 "DELETE request first.".format(used_by)})
            return
        setattr(self.module, 'used_by', auth.user_by_token(self.api_token))
        global ws
        # Send update to all clients via WS
        ws.update_lock(hwconf.modules.index(self.module),
                       getattr(self.module, 'used_by', None))
        self.finish("OK")

    def delete(self):
        """ Force to remove any user lock from the module """
        used_by = getattr(self.module, 'used_by', None)
        if used_by is None:
            self.set_status(400)
            self.finish({'error': 'Module is not used by anyone at the moment'})
            return
        setattr(self.module, 'used_by', None)
        # Send update to all clients via WS
        global ws
        ws.update_lock(hwconf.modules.index(self.module),
                       getattr(self.module, 'used_by', None))
        self.finish("OK")

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
        # This check is not applicable to broadcast module (slot 0)
        if self.slot and used_by != auth.user_by_token(self.api_token):
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
    """API function that opens/closes WebSocket connection and
    provides interface to send data through the WebSocket"""
    allow_broadcast = False

    def update_module(self, added, slot):
        """Send update to clients indicating that module has been added or
        removed
        """
        message = {
            'msg_type': 'MODULE_UPDATE',
            'slot': slot,
            'module_name': getattr(hwconf.modules[slot], 'name', None),
            'added': added
        }
        self.write_message(message)

    def update_lock(self, slot, used_by):
        """Send update to clients indicating that module has been locked or
        unlocked
        """
        message = {
            'msg_type': 'LOCK_UPDATE',
            'slot': slot,
            'used_by': used_by
        }
        self.write_message(message)

    def send_data(self, slot, data):
        """Send data generated by a module to clients"""
        message = {
            'msg_type': 'DATA_UPDATE',
            'slot': slot,
            'data': data
        }
        self.write_message(message)

    def open(self):
        """Open WebSocket connection"""
        global ws
        ws = self
        # add update_module function as a callback to hwconf module
        hwconf.callbacks.append(self.update_module)

    def close(self, **kwargs):
        """Close WebSocket connection"""
        # remove update_module function as a callback to hwconf module
        hwconf.callbacks.remove(self.update_module)

    def on_message(self, message):
        """This method is for testing purposes and simply echoes received
        messages
        """
        self.write_message('Echo:' + message)


class BaseWebHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return auth.user_by_token(
            self.get_cookie(options.session_cookie_name))

    @tornado.web.authenticated
    def prepare(self):
        super(BaseWebHandler, self).prepare()


class IndexPageHandler(BaseWebHandler):

    @tornado.gen.coroutine
    def get(self):
        # Web interface (except admin console is built to support static
        # templates, so it does not use any template variables. All information
        # in web UI is rendered by means of REST API
        # The only reason to have separate handler instead of redirect to static
        # file is to wrap .get() method in authenticated decorator
        self.render("index.html")


class AdminConsoleHandler(tornado.web.RequestHandler):
    """ Admin console - system setting configuration """

    @auth.http_basic(auth.admin_auth)
    def get(self):
        self.render("admin_home.html")

    post = delete = put = get


class SystemUpgradeHandler(tornado.web.RequestHandler):
    """System upgrade page for admin page
    This handler allows to see version available on Pypi and perform update if
    it is not the latest one (actually, just run command
    `pip install --upgrade easy_phi` )
    This handler requires package to be installed into user-writable directory,
    e.g. virtualenv
    """

    @auth.http_basic(auth.admin_auth)
    def get(self):
        self.render("admin_system_upgrade.html",
                    current_version=__version__,
                    available_version=utils.get_latest_pypi_version(),
                    error=None
                    )

    @auth.http_basic(auth.admin_auth)
    def post(self):
        # This method requires certain privileges to install software
        error = None
        status = -1
        try:
            status = pip.main(['install', '-U', __project__])
        except OSError:
            error = "Insufficient permissions to run upgrade. Check system " \
                    "documentation, section System Upgrade "

        if status != 0:
            error = "Failed to upgrade package {package}, exit status " \
                    "{status}. Consult system documentation, section System " \
                    "Upgrade for troubleshooting." \
                    "".format(status=status, package=__project__)

        if error:
            self.render("admin_system_upgrade.html",
                        current_version=__version__,
                        available_version=utils.get_latest_pypi_version(),
                        error=error
                        )
            return

        # TODO: restart app (after daemonization implemented)

        self.redirect(application.reverse_url('upgrade'))


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
        self.render("404.html")

    post = put = delete = get

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

if options.security_backend == 'easy_phi.auth.DummyLoginHandler':
    # even if default security backend is dummy, user still has to visit auth
    # page before api requests will be accepted. Here is a workaround for that
    # This is only to enable api calls with dummy backend without opening web
    # interface, index page will perform authorization
    auth.register_token(options.security_dummy_username, '')

# it should start after options already parsed, as hwconf depends on certain
# options like ports configurations, timeouts etc
hwconf.start()

settings = {
    'debug': options.debug,
    'default_handler_class': PageNotFoundHandler,
    'static_url_prefix': '/static/',
    'static_handler_class': ContorlledCacheStaticFilesHandler,
    'static_path': options.static_path,
    'template_path': options.template_path,
    'login_url': '/login',
}

# URL schemas to RequestHandler classes mapping
application = tornado.web.Application([
    (r"/", IndexPageHandler, None, 'home'),
    (r"/api/v1/info", PlatformInfoHandler, None, 'api_platform_info'),
    (r"/api/v1/module", ModuleInfoHandler, None, 'api_module_info'),
    (r"/api/v1/modules_list", ModulesListHandler, None, 'api_module_list'),
    (r"/api/v1/module_scpi_list", ListSCPICommandsHandler, None,
        'api_list_commands'),
    (r"/api/v1/lock_module", SelectModuleHandler, None, 'api_select_module'),
    (r"/api/v1/send_scpi", SCPICommandHandler, None, 'api_send_scpi'),
    (r"/api/v1/module_ui_controls", ModuleUIHandler, None, 'api_widgets'),
    (r"/admin", AdminConsoleHandler, None, 'admin'),
    (r"/admin/upgrade", SystemUpgradeHandler, None, 'upgrade'),
    (r"/logout", auth.LogoutHandler, None, 'logout'),
    (r"/login", auth.LoginHandler, None, 'login'),
    (r"/websocket", WebSocketHandler)
], **settings)

if 'easy_phi.auth.PasswordAuthLoginHandler' in options.security_backends:
    application.add_handlers(".*$", [
        (r"/admin/passwords", auth.PasswordAuthAPIHandler, None, 'passwords'),
    ])

def main(application=application):
    # start hw configuration monitoring. It requires configuration of hw ports
    # so it shall be done after parsing conf file

    # we need HTTP server to serve SSL requests.
    ssl_ctx = None
    http_server = tornado.httpserver.HTTPServer(
        application, ssl_options=ssl_ctx)
    http_server.listen(options.server_port)
    tornado.ioloop.IOLoop.current().start()

    # TODO: add TCP socket handler to listen for HiSlip requests from VISA

if __name__ == '__main__':
    main(application)
