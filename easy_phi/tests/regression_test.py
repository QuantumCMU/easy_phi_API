# -*- coding: utf-8 -*-

import timeit

import tornado.testing

from easy_phi import app


class PerformanceTest(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        return app.application

    def test_timing_send_scpi(self):
        # format=plain here is just to get rid of json parsing
        modules = self.fetch('/api/v1/modules_list?format=plain')
        self.failIf(modules.error)

        if len([m for m in modules.body.split("\n") if m != "None"])>1:
            # there is some equipment connected
            self.assertTrue(False,
                            "\n" + "="*70+"\n"+
                            "Performance test shall be executed without any "
                            "equipment connected.\nOtherwise, it iwll test"
                            "performance of your equipment, not system's one.\n"
                            "Please disconnect all modules from the system and "
                            "run test again.\n"+ "="*70)

        # test if it passes one time
        response = self.fetch('/api/v1/send_scpi?format=plain&slot=0',
                              method='POST', body='*IDN?')
        self.failIf(response.error)

        # slot=0: test on Broadcast pseudo module
        # it is requested in plaintext because json encoding depends on backend
        # library (e.g. json, cjson, simplejson etc)
        # *IDN? is very simple command that should take predictable low time
        # to execute
        def fetch():
            self.fetch('/api/v1/send_scpi?format=plain&slot=0',
                       method='POST', body='*IDN?')

        # This test takes ~1.5s per 1000 cycles on i7@2.2
        elapsed = timeit.timeit(fetch, number=1000)

        # actually, unittest will print total execution time
        # but you can also output elapsed here
