# -*- coding: utf-8 -*-
import json

import tornado.testing

from easy_phi import app


class TestTornadoWeb(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        return app.application

    def testVersionHandler(self):
        self.http_client.fetch(self.get_url('/api/v1/info?format=json'), self.stop)
        response = self.wait()

        self.failIf(response.error)
        response_obj = json.loads(response.body)

        self.assertTrue('modules' in response_obj,
                        "Field 'modules' not found in platform info")


if __name__ == '__main__':
    tornado.testing.main()
