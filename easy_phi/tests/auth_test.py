# -*- coding: utf-8 -*-
import base64

import tornado.testing
from tornado.options import options

from easy_phi import app


class AdminConsoleAccessTest(tornado.testing.AsyncHTTPTestCase):

    admin_url = '/admin'

    def get_app(self):
        return app.application

    def check_auth_headers(self, response):
        self.assertIn('WWW-Authenticate', response.headers,
                      "HTTP 401 does not contain WWW-Authenticate header")
        self.assertTrue(
            response.headers['WWW-Authenticate'].startswith('Basic realm='),
            "WWW-Authenticate does not start with 'Basic realm='")

    def test_password_required(self):
        response = self.fetch(self.admin_url)

        self.assertEqual(response.code, 401,
                         "Admin console allows access without password")
        self.check_auth_headers(response)

    def test_random_valid_password(self):
        response = self.fetch(self.admin_url,
                              auth_username='Aladdin',
                              auth_password='sesame')

        self.assertEqual(response.code, 401,
                         "Admin console allows access with Aladdin:sesame pass")
        self.check_auth_headers(response)

    def test_invalid_password(self):
        response = self.fetch(
            self.admin_url,
            headers={
                # Aladdin:sesame
                'Authorization': 'Basic invalid_base64'
            })

        self.assertEqual(response.code, 401,
                         "Admin console allows access with invalid credentials")
        self.check_auth_headers(response)

    def test_valid_password(self):
        response = self.fetch(self.admin_url,
                              auth_username=options.admin_login,
                              auth_password=options.admin_password)

        self.failIf(response.error)
