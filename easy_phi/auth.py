#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Authentication functions for Easy Phi test measurement platform

Platform supports configurable security, i.e. administrator can change
security backend from web interface. It means that we don't know in advance
whether user will be authenticated by plaintext password or using Google
credentials, so we need an abstraction layer, implemented in this file.

"""
import base64
import functools
import hashlib
import json
import re
import urllib
import uuid
import subprocess
import keyring

import tornado.web
import tornado.util
import tornado.auth
import tornado.gen
from tornado.options import options, define

from easy_phi import __project__ as service

define('admin_login', default='easy-phi')
define('admin_password', default='easy-phi')

define('secret', '')
define('session_cookie_name', 'api_token')
define('session_cookie_ttl', 30)
define('session_cookie_length', 16)

define('security_backend', default='easy_phi.auth.DummyLoginHandler')
define('security_backends', default=[
    'easy_phi.auth.DummyLoginHandler',
    'easy_phi.auth.PasswordAuthLoginHandler',
    'easy_phi.auth.GoogleLoginHandler',
])

# DummyLoginHandler settings
define('security_dummy_username', 'Anonymous')

# PasswordAuthLoginHandler settings
define('security_password_auth_user_list_path',
       '/etc/easy_phi/passwords_auth_users')

# GoogleLoginHandler settings
define('security_google_oauth_client_id', '')
define('security_google_oauth_secret', '')

# map of api_tokens to authenticated users
# i.e. active_tokens[hash_value] = username
active_tokens = {}


def validate_api_token(token):
    """ Validate API access token. Since security backend is configurable,
    potentially we have backends like OAuth and Google Auth, which aren't
    easy to use from client applications on Python and Labview. Instead
    every user has api access token which is generated from auth info.

    Access token shall be generated in a consistent way, i.e. it is not
    the same as session token. Also, we do not store data offline so list
    of valid tokens generated upon user authentication and stored only in
    application memory.
    :param token: string, api token
    :return boolean, True if api token is associated with authenticated user"""

    global active_tokens

    return token in active_tokens


def user_by_token(token):
    global active_tokens
    return active_tokens.get(token)


def _token_generator():
    """Wrapper function to hide real secret value used to generate api_tokens
    """
    _secret = options.secret

    if not _secret:
        m = hashlib.md5()
        m.update(uuid.getnode().__hex__())  # MAC address
        try:
            fh = open('/etc/fstab', 'r')
            fstab = fh.read(4096)
            fh.close()
        except IOError:
            fstab = uuid.uuid1(clock_seq=0).hex

        m.update("\n".join(  # use only non-empty, non-comment lines
            filter(lambda x: x,
                 (l.split("#", 1)[0].strip() for l in fstab.split('\n')))))

        try:
            hostid = subprocess.check_output('hostid')
        except OSError:
            # 4 chosen by a fair dice roll. Guaranteed to be random :)
            hostid = uuid.uuid1(clock_seq=4).hex
        m.update(hostid)

        _secret = m.hexdigest()

    def _generate_token(username):
        """Generate unique and unpredictable token from username and intrinsic
        platform info (MAC addr, filesystem UUIDs, hostid)
        CPUID is not used since it can be predicted from HW configuration

        Generating random number and storing it somewhere in the system would
        be more secure but won't work on read-only filesystems
        """

        m = hashlib.md5()
        m.update(str(username))
        m.update(_secret)
        # return only hex part
        return m.hexdigest()[:options.session_cookie_length]

    return _generate_token


generate_token = _token_generator()


def register_token(user, api_token):
    """ Register user api_token after authentication.
    This function is intended to be used by login web handler.

    :param user: string, username
    :param api_token: token, consistent hash from auth backend
    :return: None
    """
    global active_tokens
    active_tokens[api_token] = user


def unregister_token(api_token):
    global active_tokens
    if api_token in active_tokens:
        del(active_tokens[api_token])


def admin_auth(user, password):
    """ Function to authenticate admin user
    """
    return (user == options.admin_login and
            password == options.admin_password)


def parse_http_basic_auth(request):
    """ Parse request headers and return HTTP Basic auth user, None otherwise
    """
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Basic '):
        try:
            return base64.b64decode(auth_header[6:]).split(":", 2)
        except TypeError:
            pass
    return None, None


def http_basic(auth_func):
    """ Decorator for admin console handler functions
    It is different from general user login because of configurable security
    backends. Administrator password is stored in plaintext in options file

    At the same time, admin account does not have access to API

    Admin login is performed using HTTP Basic authentication
    """

    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            user, pwd = parse_http_basic_auth(self.request)
            if not auth_func(user, pwd):
                self.set_header('WWW-Authenticate',
                                'Basic realm=Easy Phi administration console')
                self.set_status(401)
                self.finish("Authentication required")
            else:
                method(self, *args, **kwargs)

        return wrapper

    return decorator


class LogoutHandler(tornado.web.RequestHandler):
    """ Universal logout handler for all security backends """

    def get(self):
        unregister_token(options.session_cookie_name)
        self.clear_cookie(options.session_cookie_name)
        self.redirect('/')


class LoginHandler(tornado.web.RequestHandler, tornado.util.Configurable):
    """ Special class to support configurable security backend """

    @classmethod
    def configurable_base(cls):
        # it has to be LoginHandler, otherwise configurable_default is not used
        return LoginHandler

    @classmethod
    def configurable_default(cls):
        # we know that options.security_backend is a string, not a class
        # need to import it first
        return tornado.util.import_object(options.security_backend)

    def __new__(cls, *args, **kwargs):
        """ Well, it's a long story.
        tornado.util.Configurable uses initialize() instead of __init__ to
        support singleton magic in AsyncHTTPClient (see comments in
        tornado.util.Configurable.__new__ for details)

        tornado.web.RequestHandler expects parameters to be passed to __init__()
        It also has empty initialize() method without parameters.

        Here we don't depend on initialize(), and we need to call handler's
        __init__().  here is why __new__ is overridden  to call __init__
        and initialize() is extended to accept args and kwargs
        """
        instance = super(LoginHandler, cls).__new__(cls, *args, **kwargs)
        instance.__init__(*args, **kwargs)
        return instance

    def initialize(self, *args, **kwargs):
        pass

    def authenticate(self, username, token=None):
        """ Helper method to do user authentication in a uniform way
        Call this method from .get() or .post() methods in login handler
        """
        if token is None:
            token = generate_token(username)
        register_token(username, token)
        self.set_cookie(options.session_cookie_name, token,
                        expires_days=options.session_cookie_ttl)

        # Username cookie is not used for authentication. It is only a
        # convenience shortcut to display username in web UI
        self.set_cookie('username', username,
                        expires_days=options.session_cookie_ttl)

        next_url = self.get_argument('next', '') or \
            self.request.headers.get('Referer') or \
            '/'
        self.redirect(next_url)


class DummyLoginHandler(LoginHandler):
    """ Dummy security backend - accept everybody without questions """

    @tornado.gen.coroutine
    def get(self):
        """Dummy backend will silently accept any user without password """
        # But since it is a dummy handler, we assign empty api token and
        # default username for everybody
        self.authenticate(options.security_dummy_username, '')

    post = get

_user_cache = None


class PasswordAuthAPIHandler(tornado.web.RequestHandler):
    user = None
    password = None

    # this method is static to be used by check_passwords, which is in turn
    # static to be used by PasswordAuthLoginHandler without class instantiation
    @staticmethod
    def get_users():
        global _user_cache
        if _user_cache is None:
            try:
                fh = open(options.security_password_auth_user_list_path, 'r')
            except IOError:
                return None
            users = [line.split("#", 1)[0].strip() for line in fh]
            _user_cache = sorted([user for user in users if user])
        return _user_cache

    @staticmethod
    def set_users(users):
        global _user_cache
        try:
            fh = open(options.security_password_auth_user_list_path, 'w')
            fh.write("\n".join(sorted(users)))
        except IOError:
            return False
        fh.close()
        _user_cache = None
        return True

    @staticmethod
    def check_password(username, password):
        """ Check if user is registered user and password matches stored one """
        users = PasswordAuthAPIHandler.get_users() or []
        return username in users \
            and password == keyring.get_password(service, username)

    @http_basic(admin_auth)
    def prepare(self):
        self.set_header('Content-Type', 'text/plain')
        users = PasswordAuthAPIHandler.get_users()
        if users is None:
            self.set_status(403)
            self.finish('Password authorization is not configured properly. '
                        'Please check system documentation.')
            return

        if self.request.method in ('POST', 'DELETE', 'HEAD'):
            user = self.get_argument('user')
            if user not in users:
                self.set_status(404)
                self.finish('User {user} not found'.format(user=user))
                return
            self.user = user

        if self.request.method in ('POST', 'PUT'):
            # "or ''" is to handle PUT/POST without body
            password = self.request.body or ''
            if not 5 < len(password) < 31 or not re.search("\d", password) \
                    or not re.search("[a-zA-Z]", password):
                self.set_status(400)
                self.finish('Password is missing or does not match safety '
                            'criteria. Password should be 6 to 30 characters '
                            'long, contain at least one digit and at least one '
                            'letter.')
                return
            self.password = password

    def get(self):
        """List users (ajax) or render passwords management page (otherwise)"""
        users = PasswordAuthAPIHandler.get_users()
        # Ajax
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # i.e. it is ajax request
            self.finish("\n".join(users))
            return
        # Non- Ajax
        self.clear()  # reset content-type
        self.render('admin_manage_passwords.html', users=users)

    def head(self):
        """Return length of user password
        Please note that password itself will be ignored, it is to get length
        only and used either to generate stars in password field and testing
        """
        self.set_header("Content-Length",
                        len(keyring.get_password(service, self.user)))

    def put(self):
        """Create new user """
        user = self.get_argument('user', '')

        if len(user) < 4 or not re.match("[a-zA-Z][\w_]{3,19}$", user):
            self.set_status(400)
            self.finish('Username is missing or invalid. User name should '
                        'start with letter, and contain only alphanumeric '
                        'characters, dashes or underscores, and be 4 to 20 '
                        'characters long.')
            return

        if user in PasswordAuthAPIHandler.get_users():
            self.set_status(400)
            self.finish('User already exists')
            return

        users = PasswordAuthAPIHandler.get_users() + [user]
        if not PasswordAuthAPIHandler.set_users(users):
            self.set_status(403)
            self.finish('Can not create user. Please consult system '
                        'documentation, section Security - Password backend')
            return
        self.finish('User {user} successfully created'.format(user=user))

    def delete(self):
        """Delete user """
        users = [user for user in PasswordAuthAPIHandler.get_users()
                 if user != self.user]
        if not PasswordAuthAPIHandler.set_users(users):
            self.set_status(403)
            self.finish('Can not delete user. Please consult system '
                        'documentation, section Security - Password backend')
            return
        self.finish('User {user} successfully deleted.'.format(user=self.user))

    def post(self):
        """Change user passowrd """
        keyring.set_password(service, self.user, self.password)
        self.finish("User password changed successfully")


class PasswordAuthLoginHandler(LoginHandler):
    """ HTTP Basic auth security backend - request username and password """

    @tornado.gen.coroutine
    @http_basic(PasswordAuthAPIHandler.check_password)
    def get(self):
        user, pwd = parse_http_basic_auth(self.request)
        self.authenticate(user)


class GoogleLoginHandler(LoginHandler, tornado.auth.GoogleOAuth2Mixin):
    """ Google security backend - require Google login with configured domain"""
    _OAUTH_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

    def get_user_info(self, access_token):
        query = urllib.urlencode({
            'alt': 'json',
            'access_token': access_token
        })
        response = urllib.urlopen(self._OAUTH_USERINFO_URL + '?' + query)
        return json.loads(response.read())

    def prepare(self):
        super(GoogleLoginHandler, self).prepare()
        self.settings['google_oauth'] = {
            'key': options.security_google_oauth_client_id,
            'secret': options.security_google_oauth_secret
        }

    @tornado.gen.coroutine
    def get(self):
        """
        1. User gets to this handler, 'code' is not provided
        2. handler redirects user to OAuth handler by calling authorize_redirect
        3. OAuth provider authenticates user and creates temprorary token, then
            redirects user to provided redirect_uri with token in 'code'
        4. User gets to this handler having 'code'.
        5. tornado.auth.GoogleOAuth2Mixin checks token
        6
        For more details check
            http://tornado.readthedocs.org/en/latest/auth.html
        """
        redirect_uri = "{proto}://{host}{uri}".format(
            proto=self.request.protocol,
            host=self.request.host or 'localhost',
            uri=self.request.path)
        if self.get_argument('code', False):
            auth_info = yield self.get_authenticated_user(
                redirect_uri=redirect_uri + '',
                code=self.get_argument('code'))

            userinfo = self.get_user_info(auth_info['access_token'])
            self.authenticate(userinfo['email'])
        else:
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                # see https://developers.google.com/+/web/api/rest/oauth
                # for other profiles. Usually ['profile', 'email'] is enough
                scope=['email'],
                response_type='code',
                extra_params={'approval_prompt': 'auto'})
