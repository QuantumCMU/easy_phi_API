# -*- coding: utf-8 -*-

""" Unit tests for Tornado web app handlers of Easy Phi platform """

import json

import tornado.testing
from tornado.options import options
import tornado.websocket
from tornado import gen

from easy_phi import app


class BaseTestCase(tornado.testing.AsyncHTTPTestCase):
    """ common setup procedure for all API calls, e.g. creating api token """
    headers = None
    url = None
    format = 'json'
    url_name = ''

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.url = self._app.reverse_url(self.url_name)
        if self.format is not None:
            self.url += '?format=' + self.format

    def get_app(self):
        options.security_backend = 'easy_phi.auth.DummyLoginHandler'
        # just and example how to set cookie:
        # self.headers = {"Cookie": '='.join((options.session_cookie_name,
        #                                    api_token))}
        return app.get_application()


class PlatformInfoTest(BaseTestCase):

    url_name = 'api_platform_info'

    def test_response(self):
        """ Test if platform info method output makes sense """
        response = self.fetch(self.url, headers=self.headers)
        self.failIf(response.error)

        response_obj = json.loads(response.body)

        for field in ('slots', 'sw_version', 'hw_version', 'vendor'):
            self.assertTrue(
                field in response_obj,
                "Field '{0}' not found in platform info".format(field))


class ContentTypeTest(BaseTestCase):

    url_name = 'api_platform_info'
    format = None

    def test_content_type(self):
        """ Test if API returns correct Content-Type for different formats.
        This test is not related to platform info, but has similar setup """
        response = self.fetch(self.url+'?format=json', headers=self.headers)
        self.assertTrue(
            response.headers.get('Content-Type', '').startswith(
                'application/json'),
            "Wrong response content type for 'format=json'")

        response = self.fetch(self.url+'?format=plain', headers=self.headers)
        self.assertTrue(
            response.headers.get('Content-Type', '').startswith(
                'text/plain'),
            "Wrong response content type for 'format=plain'")


class ModuleInfoTest(BaseTestCase):

    url_name = 'api_module_info'

    def test_module_info(self):
        """ Test module info API call output contains correct fields"""
        # testing on Broadcast pseudo-module
        # TODO: use pseudo device to check interaction with pyudev.Device
        response = self.fetch(self.url+'&slot=0', headers=self.headers)

        self.failIf(response.error)
        response_obj = json.loads(response.body)

        self.assertIsInstance(
            response_obj, dict,
            "modules_list expected to return dictionary")

        fields = ('name', 'sw_version', 'hw_version', 'vendor', 'serial_no')
        for field in fields:
            self.assertTrue(
                field in response_obj,
                "Field '{0}' not found in module info".format(field))


class ModuleListTest(BaseTestCase):

    url_name = 'api_module_list'

    def test_modules_list(self):
        """ Test module list API call actually produces a list"""
        response = self.fetch(self.url, headers=self.headers)

        self.failIf(response.error)
        response_obj = json.loads(response.body)

        self.assertIsInstance(
            response_obj, list,
            "modules_list expected to return list")

        self.assertTrue(len(response_obj) > 0,
                        "modules_list returned empty list")
        for module in response_obj:
            self.assertTrue(
                module is None or isinstance(module, basestring),
                "module in modules_list expected to be string or None")


class ListSCPICommandsTest(BaseTestCase):

    url_name = 'api_list_commands'

    def test_list_scpi_commands(self):
        """ Test list supported SCPI commands API call """
        # test on Broadcast pseudo module
        response = self.fetch(self.url+'&slot=0',
                              headers=self.headers)

        self.failIf(response.error)
        response_obj = json.loads(response.body)

        self.assertIsInstance(
            response_obj, list,
            "module_scpi_list expected to return list of commands")

        self.assertTrue(len(response_obj) > 0,
                        "module_scpi_list returned empty list")

        for command in response_obj:
            self.assertIsInstance(
                command, basestring,
                "SCPI command expected to be string")


class SCPICommandTest(BaseTestCase):
    """ Test sending SCPI commands to a module """

    url_name = 'api_send_scpi'

    def test_slot_validation(self):
        """ Check slot parameter is properly validated """
        # test on Broadcast pseudo module
        response = self.fetch(self.url, method='POST', body='*IDN?',
                              headers=self.headers)

        self.assertEqual(
            response.code, 400,
            "Request without slot number did not cause error response")

        response = self.fetch(self.url+'&slot=aaa',
                              method='POST', body='*IDN?', headers=self.headers)

        self.assertEqual(
            response.code, 400,
            "Request with non-numeric slot number did not cause error response")

        response = self.fetch(self.url+'&slot=65535',
                              method='POST', body='*IDN?', headers=self.headers)

        self.assertEqual(
            response.code, 400,
            "Request with slot number bigger than available ports"
            "did not cause error response")

    def test_systemwide_scpi_command(self):
        """ Check system-wide command works
        System wide commands are special SCPI commands handled by broadcast
        module. Usually they represent some platform-level functions, e.g.
        return platform configuration
        """
        response = self.fetch(self.url+'&slot=0', method='POST',
                              body='RAck:Size?', headers=self.headers)

        self.failIf(response.error)
        response_obj = json.loads(response.body)

        self.assertIsInstance(
            response_obj, int,
            "Systemwide command RAck:Size? didn not return integer. "
            "Actual response: {response}".format(response=response.body)
        )
        self.assertGreaterEqual(
            response_obj, len(options.ports),
            "Systemwide command RAck:Size? returned less than ports number")

        response = self.fetch(self.url+'&slot=0', method='POST',
                              body='SYSTem:VERSion?', headers=self.headers)

        self.failIf(response.error)
        response_obj = json.loads(response.body)
        self.assertIsInstance(
            response_obj, basestring,
            "Systemwide SCPI command SYSTem:VERSion? returned non-string")

    def test_attempt_real_scpi_command(self):
        """ Test real SCPI command if module is available """
        response = self.fetch(
            self._app.reverse_url('api_module_list')+'?format=json',
            headers=self.headers)

        self.failIf(response.error, "Module list returned error")
        modules = json.loads(response.body)
        for slot, module in enumerate(modules[1:]):
            if module is not None:
                response = self.fetch(
                    self.url+'&slot={0}'.format(slot+1),
                    method='POST', body='*IDN?')
                response_obj = json.loads(response.body)
                self.assertIsInstance(
                    response_obj, basestring,
                    "Module SCPI command expected to return string, received: "
                    "{0}".format(response.body))


class ModuleUIHandlerTest(BaseTestCase):

    url_name = 'api_widgets'
    format = None

    def test_format_ignored(self):
        # test on Broadcast pseudo module
        response = self.fetch(self.url+"?slot=0&container=t",
                              headers=self.headers)
        self.failIf(response.error)
        self.assertEqual(response.headers.get('Content-Type'),
                         "application/javascript",
                         "Wrong content type for widgets if format omitted")

        response = self.fetch(self.url+"?format=json&slot=0&container=t",
                              headers=self.headers)
        self.failIf(response.error)
        self.assertEqual(response.headers.get('Content-Type'),
                         "application/javascript",
                         "Wrong content type for widgets if format json")

        response = self.fetch(self.url+"?format=plain&slot=0&container=t",
                              headers=self.headers)
        self.failIf(response.error)
        self.assertEqual(response.headers.get('Content-Type'),
                         "application/javascript",
                         "Wrong content type for widgets if format is plain")

    def test_required_params(self):
        response = self.fetch(self.url+"?slot=0", headers=self.headers)

        self.assertEqual(
            response.code, 400,
            "Request without container selector did not cause error response")

        response = self.fetch(self.url+"?container=.blah",
                              headers=self.headers)

        self.assertEqual(
            response.code, 400,
            "Request without slot number did not cause error response")

    def test_mime_type(self):
        # test on Broadcast pseudo module
        response = self.fetch(self.url+"?slot=0&container=%23blah",
                              headers=self.headers)

        self.failIf(response.error, "ModuleUI handler returned error")
        self.assertEqual(
            response.headers.get('Content-type'), 'application/javascript',
            "ModuleUI handler returned wrong content type "
            "('application/javascript' expected)"
        )


class WebSocketBaseTestCase(tornado.testing.AsyncHTTPTestCase):

    @gen.coroutine
    def ws_connect(self, path, compression_options=None):
        ws = yield tornado.websocket.websocket_connect(
            'ws://127.0.0.1:%d%s' % (self.get_http_port(), path),
            compression_options=compression_options)
        raise gen.Return(ws)

    @gen.coroutine
    def close(self, ws):
        """Close a websocket connection and wait for the server side.
        If we don't wait here, there are sometimes leak warnings in the
        tests.
        """
        ws.close()


class WebSocketTest(WebSocketBaseTestCase):

    def get_app(self):
        return app.get_application()

    @tornado.testing.gen_test
    def test_websocket_gen(self):
        ws = yield self.ws_connect('/websocket')
        ws.write_message('hello')
        response = yield ws.read_message()
        self.assertEqual(response, 'Echo:hello')
        yield self.close(ws)
