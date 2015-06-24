# -*- coding: utf-8 -*-
import json

import tornado.testing

from easy_phi import app


class TestRegressionSCPIHandler(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        return app.application

    def TestRegressionSCPIHandler(self):
        response = self.fetch('/api/v1/module?slot=3{*IDN?}’)

	self.failIf(response.error)
        self.assertEqual(response.code, 302)

