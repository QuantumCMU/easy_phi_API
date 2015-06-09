#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file contains Web Application
"""
import os

import tornado.ioloop
import tornado.httpserver
import tornado.web
from tornado.options import options, parse_config_file, define

import hwconf
from decorators import multiformat

VERSION = "0.1"
LICENSE = "GPL v3.0"
PROJECT = "easy_phi"

# configuration defaults
define("conf_path", default="/etc/easy_phi.conf")
define("static_path", default=os.path.join(os.path.dirname(__file__), '..', 'static'))
define("server_port", default=8000)
define("default_format", default='json')
define("hw_version", default='N/A')
define("vendor", type=str)

define("debug", default=True)

settings = {
    'autoreload': options.debug,
}


class APIHandlerMetaclass(type):
    """ Metaclass to apply multiformat decorator to all REST methods """
    def __new__(cls, name, bases, dct):
        # Now, get/put/post/whatever method can return object instead of self.write-ing
        handler = super(APIHandlerMetaclass, cls).__new__(cls, name, bases, dct)

        for method in ('get', 'post', 'put', 'head', 'delete'):
            setattr(handler, method, multiformat(getattr(handler, method)))

        return handler


class APIHandler(tornado.web.RequestHandler):
    """ Tornado handlers subclass to format response into xml/json/plain """
    __metaclass__ = APIHandlerMetaclass


class ModuleHandler(APIHandler):
    """ APIHandler subclass to handle slot number validation
    It is intended for handlers working with modules """
    allow_broadcast = False
    slot = None

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


class PlatformInfoHandler(APIHandler):
    """ Return basic info about the system """
    def get(self):
        return {
            'sw_version': VERSION,
            'hw_version': options.hw_version,
            'vendor': options.vendor,
            'slots': len(hwconf.modules),
            'supported_api_versions': [1],
            'modules': [module and module.name for module in hwconf.modules],
        }


class SelectModuleHandler(ModuleHandler):
    """Select the module, identified by ID passed as a URL parameter.
    get, head: get status
    put:    set lock
    delete: remove lock
    post:   change status
    """
    allow_broadcast = False

    def post(self):
        """ Set user lock on module to indicate it is used by someone """
        session = self.get_argument("session")
        # Check the status of selected module (must be unlocked) [TBD]

        # Lock the module [TBD]

        # Redirect user to a constructed Module specific web-page [TBD]

        return "OK"

    def delete(self):
        """ Set user lock on module to indicate it is used by someone """
        return "OK"

    def get(self):
        """ Return user lock status of the module
        :param: id: integer, slot number 1...N
        :return: user name of the person using this module, None otherwise
        """
        response = None
        return response


class SCPICommandHandler(ModuleHandler):
    """API functions related to a module in the specified rack slot"""
    allow_broadcast = True

    def post(self):
        """Transfer SCPI command to a module and return the response"""
        scpi_command = self.request.body
        if not scpi_command:
            err = "scpi command expected"
        if err:
            self.set_status(400)
            self.finish({'error': err})
            return

        module = hwconf.modules[self.slot]
        response = module.scpi()
        return response

    def get(self):
        """Get module configuration (i.e. list of available SCPI commands)"""
        module = hwconf.modules[self.slot]
        return module.get_configuration()


class AdminConsoleHandler(tornado.web.RequestHandler):
    """Redirect user to Admin Console web-page"""

    def get(self):
        # Debug purpose only

        response = {'handler': 'AdminConsoleHandler'}
        return response

# URL schemas to RequestHandler classes mapping
application = tornado.web.Application([
    (r"/", tornado.web.RedirectHandler,
        {"url": '/static/index.html'}),
    (r"/api/v1/", PlatformInfoHandler),
    (r"/api/v1/module/select", SelectModuleHandler),
    (r"/api/v1/module", SCPICommandHandler),
    (r"/admin", AdminConsoleHandler),
    (r"/static/(.*)", tornado.web.StaticFileHandler,
        {"path": options.static_path}),
], **settings)

if __name__ == '__main__':
    parse_config_file(options.conf_path)
    hwconf.start()

    # we need HTTP server to serve SSL requests.
    ssl_ctx = None
    http_server = tornado.httpserver.HTTPServer(application, ssl_options=ssl_ctx)
    http_server.listen(options.server_port)
    tornado.ioloop.IOLoop.current().start()

    # TODO: add TCP socket handler to listen for HiSlip requests from VISA
