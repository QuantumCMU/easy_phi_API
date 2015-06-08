#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file contains Web Application
"""
import os
import json
import dicttoxml
import tornado.ioloop
import tornado.httpserver
import tornado.web
from datetime import date
from tornado.options import options, parse_config_file, define

import hwconf

# deifne used tornado.options
VERSION = "0.1"
LICENSE = "GPL v3.0"
PROJECT = "easy_phi"

# configuration defaults
define("conf_path", default="/etc/easy_phi.conf")
define("static_path", default=os.path.join(os.path.dirname(__file__), '..', 'static'))
define("server_port", default=8000)

define("debug", default=False)

settings = {
    'autoreload': options.debug,
}


def format(func):
    """
    This Decorator formats the output of function func
    into one of the following formats: json/xml/plain text based
    on the value of format HTTP request argument
    :param func: function to be called by the Decorator
    :return: wrapper function
    """
    def wrapper(self):
        format = self.get_argument('format', 'json')
        res = func(self)
        if format == 'json':
            self.write(json.dumps(res))
        elif format == 'xml':
            self.write(dicttoxml.dicttoxml(res))
        else:
            self.write(res)
    return wrapper

class PlatformInfoHandler(tornado.web.RequestHandler):
    """
    Return Rack software verion and last release date
    """
    @format
    def get(self):
        response = {'version': VERSION,
                    'last_build': date.today().isoformat()}
        return response


class ModulesListHandler(tornado.web.RequestHandler):
    """
    ModulesListHandler
    Return a list of modules currently connected to the Rack
    with their information
    Module information includes:
    - Module ID
    - Module Description
    - Module Software version
    - Current status: locked/unlocked
    - List of supported SCPI commands
"""
    @format
    def get(self):
        response = {'Slot1': 'Module1',
                    'Slot2': 'Module2'}
        return response


class SelectModuleHandler(tornado.web.RequestHandler):
    """Select the module, identified by ID passed as a URL parameter."""
    @format
    def post(self):
        # Parse request URL and derive moduleID [TBD]

        # Check the status of selected module (must be unlocked) [TBD]

        # Lock the module [TBD]

        # Redirect user to a constructed Module specific web-page [TBD]

        response = {'handler': 'SelectModuleHandler'}
        return response

    @format
    def get(self):
        # Debug purpose only

        response = {'handler': 'SelectModuleHandler'}
        return response


class SCPICommandHandler(tornado.web.RequestHandler):
    """Transfer SCPI command to a module, specified by moduleID"""

    @format
    def post(self):
        # Parse request URL and derive moduleID [TBD]

        # Transfer SCPI command to the module [TBD]

        # Update web-page accordingle [TBD]
        response = {'handler': 'SCPICommandHandler'}
        return response

    @format
    def get(self):
        # Debug purpose only

        response = {'handler': 'SCPICommandHandler'}
        return response


class AdminConsoleHandler(tornado.web.RequestHandler):
    """Redirect user to Admin Console web-page"""

    @format
    def post(self):
        # Redirect user to Admin Console web-page [TBD]

        response = {'handler': 'AdminConsoleHandler'}
        return response

    @format
    def get(self):
        # Debug purpose only

        response = {'handler': 'AdminConsoleHandler'}
        return response

# URL schemas to RequestHandler classes mapping
application = tornado.web.Application([
    (r"/", tornado.web.RedirectHandler,
        {"url": '/static/index.html'}),
    (r"/api/info", PlatformInfoHandler),
    (r"/api/modules", ModulesListHandler),
    (r"/api/module", SelectModuleHandler),
    (r"/api/scpi", SCPICommandHandler),
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
