#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file contains Web Application
"""

import tornado.ioloop
import tornado.web
from datetime import date
from . import VERSION, SERVER_PORT


class VersionHandler(tornado.web.RequestHandler):
    """
    Return Rack software verion and last release date
    """

    def get(self):
        response = {'version': VERSION,
                    'last_build': date.today().isoformat()}
        self.write(response)


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

    def get(self):
        response = {'module3': 'module3_info',
                    'module2': 'module2_info',
                    'module1': 'module1_info'}
        self.write(response)


class SelectModuleHandler(tornado.web.RequestHandler):
    """Select the module, identified by ID passed as a URL parameter."""

    def post(self):
        # Parse request URL and derive moduleID [TBD]

        # Check the status of selected module (must be unlocked) [TBD]

        # Lock the module [TBD]

        # Redirect user to a constructed Module specific web-page [TBD]

        response = {'handler': 'SelectModuleHandler'}
        self.write(response)

    def get(self):
        # Debug purpose only

        response = {'handler': 'SelectModuleHandler'}
        self.write(response)


class SCPICommandHandler(tornado.web.RequestHandler):
    """Transfer SCPI command to a module, specified by moduleID"""

    def post(self):
        # Parse request URL and derive moduleID [TBD]

        # Transfer SCPI command to the module [TBD]

        # Update web-page accordingle [TBD]
        response = {'handler': 'SCPICommandHandler'}
        self.write(response)

    def get(self):
        # Debug purpose only

        response = {'handler': 'SCPICommandHandler'}
        self.write(response)


class AdminConsoleHandler(tornado.web.RequestHandler):
    """Redirect user to Admin Console web-page"""

    def post(self):
        # Redirect user to Admin Console web-page [TBD]

        response = {'handler': 'AdminConsoleHandler'}
        self.write(response)

    def get(self):
        # Debug purpose only

        response = {'handler': 'AdminConsoleHandler'}
        self.write(response)

# URL schemas to RequestHandler classes mapping
APPLICATION = tornado.web.Application([
    (r"/", VersionHandler),  # Default page
    (r"/version", VersionHandler),
    (r"/modules", ModulesListHandler),
    (r"/pick_module", SelectModuleHandler),
    (r"/send_command", SCPICommandHandler),
    (r"/admin", AdminConsoleHandler)
])

if __name__ == '__main__':
    # listen for HTTP requests on TCP port
    APPLICATION.listen(SERVER_PORT)
    tornado.ioloop.IOLoop.current().start()
