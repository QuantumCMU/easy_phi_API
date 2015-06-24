# -*- coding: utf-8 -*-
import json

import tornado.testing

from easy_phi import app


class PlatformInfoTest(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        return app.application

    def testVersionHandler(self):
        response = self.fetch('/api/v1/info?format=json')

        self.failIf(response.error)
        response_obj = json.loads(response.body)

        self.assertTrue('modules' in response_obj,
                        "Field 'modules' not found in platform info")
