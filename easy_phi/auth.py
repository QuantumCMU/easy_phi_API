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

from tornado.options import options, define


define('admin_login', default='easy-phi')
define('admin_password', default='easy-phi')
define('security_backend', 'easy_phi.auth.dummy')
define('security_backends', default=[
    'easy_phi.auth.dummy'
])

# map of api_tokens to authenticated users
# i.e. active_tokens[hash_value] = username
active_tokens = {'temporary_token': 'Somebody'}


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
    # TODO: remove debug auth after configurable security is implemented
    return token in active_tokens or options.debug


def user_by_token(token):
    global active_tokens
    return active_tokens.get(token)


def register_token(user, api_token):
    """ Register user api_token after authentication.
    This function is intended to be used by login web handler.

    :param user: string, username
    :param api_token: token, consistent hash from auth backend
    :return: None
    """
    global active_tokens
    active_tokens[api_token] = user


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


class Dummy(tornado.web.RequestHandler):
    def get(self):
        pass
