# -*- coding: utf-8 -*-
import base64

import tornado.testing
from tornado.test.util import unittest
from tornado.options import options

from easy_phi import app
from easy_phi import auth


class AdminConsoleAccessTest(tornado.testing.AsyncHTTPTestCase):

    url = None

    def setUp(self):
        super(AdminConsoleAccessTest, self).setUp()
        self.url = self._app.reverse_url('admin')

    def get_app(self):
        return app.application

    def check_auth_headers(self, response):
        self.assertIn('WWW-Authenticate', response.headers,
                      "HTTP 401 does not contain WWW-Authenticate header")
        self.assertTrue(
            response.headers['WWW-Authenticate'].startswith('Basic realm='),
            "WWW-Authenticate does not start with 'Basic realm='")

    def test_password_required(self):
        response = self.fetch(self.url)

        self.assertEqual(response.code, 401,
                         "Admin console allows access without password")
        self.check_auth_headers(response)

    def test_random_valid_password(self):
        response = self.fetch(self.url,
                              auth_username='Aladdin',
                              auth_password='sesame')

        self.assertEqual(response.code, 401,
                         "Admin console allows access with Aladdin:sesame pass")
        self.check_auth_headers(response)

    def test_invalid_password(self):
        response = self.fetch(
            self.url,
            headers={
                # Aladdin:sesame
                'Authorization': 'Basic invalid_base64'
            })

        self.assertEqual(response.code, 401,
                         "Admin console allows access with invalid credentials")
        self.check_auth_headers(response)

    def test_valid_password(self):
        response = self.fetch(self.url,
                              auth_username=options.admin_login,
                              auth_password=options.admin_password)

        self.failIf(response.error)


class AuthUtilsTest(unittest.TestCase):

    def test_generate_token(self):
        token1 = auth.generate_token('foo_user')
        token2 = auth.generate_token('bar_user')
        self.assertEqual(token1, auth.generate_token('foo_user'))
        self.assertEqual(token2, auth.generate_token('bar_user'))


class DummySecurityBackendTest(tornado.testing.AsyncHTTPTestCase):

    def setUp(self):
        super(DummySecurityBackendTest, self).setUp()
        options.security_backend = 'easy_phi.auth.DummyLoginHandler'

    def get_app(self):
        return app.application

    def test_no_passwd_required(self):
        response = self.fetch(self._app.reverse_url('login')+'?next=/')

        self.assertEqual(response.code, 302,
                         "Dummy authorization backend did not redirect without "
                         "password. Response status: {0}".format(
                             response.code))

        response = self.fetch(self._app.reverse_url('logout'))

        self.assertEqual(response.code, 302,
                         "Dummy authorization backend did not redirect without "
                         "password. Response status: {0}".format(
                             response.code))
