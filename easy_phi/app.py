#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.ioloop
import tornado.web
from datetime import date

from tornado.options import define, options

#TCP port for Http requests
PORT = 8888

"""
VersionHandler

Return Rack software verion and last release date
"""
class VersionHandler(tornado.web.RequestHandler):
    def get(self):
		
        response = { 'version': '0.0.1',
                     'last_build':  date.today().isoformat() }
        self.write(response)

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
class ModulesListHandler(tornado.web.RequestHandler):
    def get(self):
        response = { 'module3' : 'module3_info',
					 'module2' : 'module2_info',
					 'module1' : 'module1_info'}
        self.write(response)

"""
SelectModuleHandler

Select the module, identified by ID passed as a URL parameter. 
"""
class SelectModuleHandler(tornado.web.RequestHandler):
    def post(self):
        #Parse request URL and derive moduleID [TBD]
		
        #Check the status of selected module (must be unlocked) [TBD]
		
        #Lock the module [TBD]
		
        #Redirect user to a constructed Module specific web-page [TBD]
        
        response = { 'SelectModuleHandler' }
        self.write(response)
"""
SCPICommandHandler

Transfer SCPI command to a module, specified by moduleID
"""
class SCPICommandHandler(tornado.web.RequestHandler):
    def post(self):
        #Parse request URL and derive moduleID [TBD]
		
        #Transfer SCPI command to the module [TBD] 
		
        #Update web-page accordingle [TBD]    
        response = { 'SCPICommandHandler' }
        self.write(response)
"""
AdminConsoleHandler

Redirect user to Admin Console web-page
"""
class AdminConsoleHandler(tornado.web.RequestHandler):
    def post(self):
		
        #Redirect user to Admin Console web-page [TBD]
        
        response = { 'AdminConsoleHandler' }
        self.write(response)
  
#URL schemas to RequestHandler classes mapping
application = tornado.web.Application([
    (r"/version", VersionHandler),
    (r"/modules", ModulesListHandler),
    (r"/pick_module", SelectModuleHandler),
    (r"/send_command", SCPICommandHandler),
    (r"/admin", AdminConsoleHandler)
])

if __name__ == '__main__':
	#listed for HTTP requests on 8888 TCP port
    application.listen(PORT)
    tornado.ioloop.IOLoop.current().start()


