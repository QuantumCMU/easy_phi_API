# -*- coding: utf-8 -*-
import unittest
import time
import json
#import timeit

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

        modules = self.fetch('/api/v1/modules_list?format=json')

        self.failIf(modules.error)
        num_modules = len(json.loads(modules.body))

        with Timer() as t:
            for i in range(1, 100):
                # test on Broadcast pseudo module
                response = self.fetch(self.api_url+'&slot=0', method='POST', body='*IDN?')
        print('Sending 100 SCPI commands took %.03f sec.' % t.interval)
        print('The number of connected modules: %.f' % num_modules)
