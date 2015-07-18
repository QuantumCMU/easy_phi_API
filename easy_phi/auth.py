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
import uuid
import subprocess

import tornado.web
import tornado.util
import tornado.auth
import tornado.gen
from tornado.options import options, define

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
define('security_passwords_file_path', '/etc/easy_phi/passwords')

# GoogleLoginHandler settings
define('security_google_login_domain', 'google.com')

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

        next_url = self.get_argument('next') or \
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


def _check_password_from_file(username, password):
    """ Utility function for password security backend
    Workflow:
        get salt from file
        calculate password hash using salt
        compare
    WARNING: for security reasons hashes in file should be different from tokens
    """
    # TODO: implement this method
    return True


class PasswordAuthLoginHandler(LoginHandler):
    """ HTTP Basic auth security backend - request username and password """

    @tornado.gen.coroutine
    @http_basic(_check_password_from_file)
    def get(self):
        user, pwd = parse_http_basic_auth(self.request)
        self.authenticate(user)


class GoogleLoginHandler(LoginHandler, tornado.auth.GoogleOAuth2Mixin):
    """ Google security backend - require Google login with configured domain"""


    @tornado.gen.coroutine
    def get(self):
        """
        For more details check
            http://tornado.readthedocs.org/en/latest/auth.html
        """
        if self.get_argument('code', False):
            user = yield self.get_authenticated_user(
                redirect_uri='http://your.site.com/auth/google',
                code=self.get_argument('code'))
            # Save the user with e.g. set_secure_cookie
        else:
            yield self.authorize_redirect(
                redirect_uri='http://your.site.com/auth/google',
                client_id=self.settings['google_oauth']['key'],
                scope=['profile', 'email'],
                response_type='code',
                extra_params={'approval_prompt': 'auto'})
