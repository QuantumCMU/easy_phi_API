# -*- coding: utf-8 -*-
import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.web
import unittest

class API_test(unittest.TestCase):

    def test_t(self):
        self.assertTrue(True)

class TestTornadoWeb(unittest.TestCase):
    http_server = None
    response = None

    def setUp(self):
        application = tornado.web.Application([
                (r'/api/v1/', PlatformInfoHandler),
                ])

        http_server = tornado.httpserver.HTTPServer(application)
        http_server.listen(8000)
    def tearDown(self):
	self.http_server.stop()

    def handle_request(self, response):
        self.response = response
        tornado.ioloop.IOLoop.instance().stop()

    def testPlatformInfoHandler(self):
        http_client = tornado.httpclient.AsyncHTTPClient()
        http_client.fetch('http://localhost:8000/api/v1/',
self.handle_request)

        tornado.ioloop.IOLoop.instance().start()

        self.failIf(self.responsse.error)
        self.assertEqual( self.response.body, "success")


if __name__ == '__main__':
    unittest.main()
