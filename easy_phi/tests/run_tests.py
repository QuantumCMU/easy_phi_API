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
    response = None

    def setUp(self):
        application = tornado.web.Application([
                (r'/', VersionHandler),
                ])

        http_server = tornado.httpserver.HTTPServer(application)
        http_server.listen(8888)

    def handle_request(self, response):
        self.response = response

        tornado.ioloop.IOLoop.instance().stop()

    def testVersionHandler(self):
        http_client = tornado.httpclient.AsyncHTTPClient()
        http_client.fetch('http://localhost:8888/version',
self.handle_request)

        tornado.ioloop.IOLoop.instance().start()

        self.failIf(self.response.error)
        self.assertEqual('success', self.response.body)


if __name__ == '__main__':
    unittest.main()
