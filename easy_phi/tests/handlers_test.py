# -*- coding: utf-8 -*-
import json

import tornado.testing

from easy_phi import app

class PlatformInfoTest(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        return app.application

    def test_response(self):
        response = self.fetch('/api/v1/info?format=json')

        self.failIf(response.error)
        response_obj = json.loads(response.body)

        for field in ('slots', 'sw_version', 'hw_version', 'vendor'):
            self.assertTrue(
                field in response_obj,
                "Field '{0}' not found in platform info".format(field))

    def test_content_type(self):
        response = self.fetch('/api/v1/info?format=json')
        self.assertTrue(
            response.headers.get('Content-Type', '').startswith(
                'application/json'),
            "Wrong response content type for 'format=json'")

        response = self.fetch('/api/v1/info?format=xml')
        self.assertTrue(
            response.headers.get('Content-Type', '').startswith(
                'application/xml'),
            "Wrong response content type for 'format=xml'")

        response = self.fetch('/api/v1/info?format=plain')
        self.assertTrue(
            response.headers.get('Content-Type', '').startswith(
                'text/plain'),
            "Wrong response content type for 'format=plain'")


class ModuleInfoTest(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        return app.application

    def test_module_info(self):
        # testing on Broadcast pseudo-module
        # TODO: use pseudo device to check interaction with pyudev.Device
        response = self.fetch('/api/v1/module?format=json&slot=0')

        self.failIf(response.error)
        response_obj = json.loads(response.body)

        self.assertTrue(isinstance(response_obj, dict),
                        "modules_list expected to return dictionary")

        for field in ('name', 'sw_version', 'hw_version', 'vendor', 'serial_no'):
            self.assertTrue(
                field in response_obj,
                "Field '{0}' not found in module info".format(field))


class ModuleListTest(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        return app.application

    def test_modules_list(self):
        response = self.fetch('/api/v1/modules_list?format=json')

        self.failIf(response.error)
        response_obj = json.loads(response.body)

        self.assertTrue(isinstance(response_obj, list),
                        "modules_list expected to return list")

        self.assertTrue(len(response_obj) > 0,
                        "modules_list returned empty list")
        for module in response_obj:
            self.assertTrue(
                module is None or isinstance(module, basestring),
                "module in modules_list expected to be string or None")


class ListSCPICommandsTest(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        return app.application

    def test_list_scpi_commands(self):
        # test on Broadcast pseudo module
        response = self.fetch('/api/v1/module_scpi_list?format=json&slot=0')

        self.failIf(response.error)
        response_obj = json.loads(response.body)

        self.assertTrue(isinstance(response_obj, list),
                        "module_scpi_list expected to return list of commands")

        self.assertTrue(len(response_obj) > 0,
                        "module_scpi_list returned empty list")

        for command in response_obj:
            self.assertTrue(isinstance(command, basestring),
                            "SCPI command expected to be string")
