# -*- coding: utf-8 -*-
import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.web
import unittest
import json
from easy_phi import app as handlers

class API_test(unittest.TestCase):

    def test_t(self):
        self.assertTrue(True)

class TestTornadoWeb(unittest.TestCase):
    http_server = None
    response = None

    def setUp(self):
        application = tornado.web.Application([
                (r'/api/v1/', handlers.PlatformInfoHandler),
                ])

        http_server = tornado.httpserver.HTTPServer(application)
        http_server.listen(8000)

    def handle_request(self, response):
        self.response = response
        tornado.ioloop.IOLoop.instance().stop()

    def test_AtLeastOneModule_PlatformInfoHandler(self):
        http_client = tornado.httpclient.AsyncHTTPClient()
        http_client.fetch('http://localhost:8000/api/v1/',
self.handle_request)

        tornado.ioloop.IOLoop.instance().start()

	expected_result = '"modules"'': ["'"Broadcast dummy module"
        
        self.failIf(self.response.error)
        assert expected_result in self.response.body
# self.assertEqual(self.response.body, expected_result_json)


if __name__ == '__main__':
    unittest.main()
