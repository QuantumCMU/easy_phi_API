# -*- coding: utf-8 -*-
import base64
import tempfile

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


class SystemUpgradeAccessTest(tornado.testing.AsyncHTTPTestCase):

    url = None

    def setUp(self):
        super(SystemUpgradeAccessTest, self).setUp()
        self.url = self._app.reverse_url('upgrade')

    def get_app(self):
        return app.application

    def test_password_required(self):
        response = self.fetch(self.url)

        self.assertEqual(response.code, 401,
                         "System Upgrade accessible without password")


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


@unittest.skipIf('easy_phi.auth.PasswordAuthLoginHandler'
                 not in options.security_backends, "Disabled in this config")
class PasswordsAuthAPITest(tornado.testing.AsyncHTTPTestCase):

    conf = None

    def setUp(self):
        options.security_backend = 'easy_phi.auth.PasswordAuthLoginHandler'

        user_list_file = tempfile.NamedTemporaryFile()
        user_list_file.write("""
        alex
          # comment line

        user2589
        mansuleman # unsorted, comment after username
        """)
        user_list_file.flush()

        options.security_password_auth_user_list_path = user_list_file.name
        self.conf = user_list_file
        self.headers = {
            'Authorization': 'Basic ' + base64.b64encode(
                ":".join((options.admin_login, options.admin_password))),
            'X-Requested-With': 'XMLHttpRequest',
        }

        super(PasswordsAuthAPITest, self).setUp()

        self.url = self._app.reverse_url('passwords')

    def get_app(self):
        return app.application

    def test_password_required(self):
        # not that auth header is not sent
        response = self.fetch(self.url)

        self.assertEqual(response.code, 401,
                         "Passwords management accessible without auth")

    def test_get_page(self):
        # designed to return full page if it is not ajax request
        headers = self.headers.copy()
        if 'X-Requested-With' in headers:
            del(headers['X-Requested-With'])

        response = self.fetch(self.url, headers=headers)
        self.failIf(response.error, "Passwords management API Ajax GET error")
        self.assertTrue(
            response.headers.get('Content-Type', '').startswith('text/html'),
            "Wrong content type returned by "
        )

    def test_put_username(self):
        password = 'Test4passwd'

        response = self.fetch(self.url, headers=self.headers)
        self.failIf(response.error, "Passwords management API Ajax GET error")
        usersb4 = response.body.split("\n")
        longest_user = max(usersb4, key=len)

        # missing user
        response = self.fetch(self.url, body=password,
                              method='PUT', headers=self.headers)
        self.assertEqual(response.code, 400)

        # user name does not match criteria

        # too short
        response = self.fetch(self.url+'?user=tre', body=password,
                              method='PUT', headers=self.headers)
        self.assertEqual(response.code, 400)

        # prohibited symbols
        response = self.fetch(self.url+"?user=try2'pwn", body=password,
                              method='PUT', headers=self.headers)
        self.assertEqual(response.code, 400,
                         "New user with special char in name can be created" +
                         response.body)

        # starts with digit
        response = self.fetch(self.url+'?user=2pac', body=password,
                              method='PUT', headers=self.headers)
        self.assertEqual(response.code, 400)

        # user name already exists
        response = self.fetch(self.url+'?user='+longest_user, body=password,
                              method='PUT', headers=self.headers)
        self.assertEqual(response.code, 400)

        # Valid request
        user = longest_user + '1'

        response = self.fetch(self.url+'?user='+user, body=password,
                              method='PUT', headers=self.headers)
        self.failIf(response.error, "User creation request failed:\n" +
                    str(response))

        response = self.fetch(self.url, headers=self.headers)
        self.failIf(response.error, "Passwords management API Ajax GET error")
        users = response.body.split("\n")
        self.assertEqual(len(users), len(usersb4)+1)
        self.assertIn(user, users)

    def test_put_password(self):
        user = 'brandon'
        # missing password
        response = self.fetch(self.url+'?user='+user, body='',
                              method='PUT', headers=self.headers)
        self.assertEqual(response.code, 400, str(response))

        # password strength does not match criteria
        # less than 6 symbols
        response = self.fetch(self.url+'?user='+user, body='test4',
                              method='PUT', headers=self.headers)
        self.assertEqual(response.code, 400)

        # no chars
        response = self.fetch(self.url+'?user='+user, body='12345678',
                              method='PUT', headers=self.headers)
        self.assertEqual(response.code, 400)

    def test_post_head(self):
        password = "Test4passwd"
        # get some existing user for experiments
        response = self.fetch(self.url, headers=self.headers)
        self.failIf(response.error, "Passwords management API Ajax GET error")
        user = response.body.split("\n", 1)[0]

        response = self.fetch(self.url+'?user='+user, body=password,
                              method='POST', headers=self.headers)
        self.failIf(response.error, "Password update request failed:\n" +
                    str(response))

        response = self.fetch(self.url+'?user='+user,
                              method='HEAD', headers=self.headers)
        self.failIf(response.error, "Password length retrieve failed:\n" +
                    str(response))
        l = int(response.headers['Content-Length'])

        self.assertEqual(l, len(password),
                         "Password stored does not match password set:\n" +
                         "{0} characters vs {1} long")

        # update it once again, just to be sure it is not the same password
        # as was stored before
        password += "1"
        response = self.fetch(self.url+'?user='+user, body=password,
                              method='POST', headers=self.headers)
        self.failIf(response.error, "Password update request failed:\n" +
                    response.body)

        response = self.fetch(self.url+'?user='+user,
                              method='HEAD', headers=self.headers)
        self.failIf(response.error, "Password length retrieve failed")
        l = int(response.headers['Content-Length'])

        self.assertEqual(l, len(password),
                         "Password stored does not match password set:\n" +
                         "{0} characters vs {1} long")

    def test_delete(self):
        # mock Ajax request
        response = self.fetch(self.url, headers=self.headers)
        self.failIf(response.error, "Passwords management API Ajax GET error")
        usersb4 = response.body.split("\n")
        user = usersb4[0]
        # we had 3 users initially and in other tests (which could be executed
        # before or after this one) they only add new users
        self.assertGreaterEqual(len(usersb4), 3)

        response = self.fetch(self.url+'?user=not_in_list',
                              method='DELETE', headers=self.headers)
        self.assertTrue(response.code >= 400,  # 400 or 404
                        "Deletion of non existent user didn't fail:\n" +
                        response.body)

        response = self.fetch(self.url+'?user='+user,
                              method='DELETE', headers=self.headers)
        self.failIf(response.error, "Passwords management API Ajax GET error")

        response = self.fetch(self.url, headers=self.headers)
        self.failIf(response.error, "Passwords management API Ajax GET error")
        users = response.body.split("\n")
        self.assertEqual(len(usersb4), len(users)+1)
        self.assertNotIn(user, users)

    def test_403(self):
        options.security_password_auth_user_list_path = '/'

        response = self.fetch(self.url, headers=self.headers)
        self.assertEqual(response.code, 403)
