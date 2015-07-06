# -*- coding: utf-8 -*-
import unittest
import time

import tornado.testing

from easy_phi import app

class Timer:
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start

class RegressionTest(tornado.testing.AsyncHTTPTestCase):
    api_url = '/api/v1/send_scpi?format=json'

    def get_app(self):
        return app.application

    def test_timing_send_scpi(self):
        i = 0
        with Timer() as t:
            while (i < 100):
                # test on Broadcast pseudo module
                response = self.fetch(self.api_url, method='POST', body='*IDN?')
                i = i + 1
        print('Sending 100 SCPI commands took %.03f sec.' % t.interval)
