#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Authentication functions for Easy Phi test measurement platform

Platform supports configurable security, i.e. administrator can change
security backend from web interface. It means that we don't know in advance
whether user will be authenticated by plaintext password or using Google
credentials, so we need an abstraction layer, implemented in this file.

"""

from tornado.options import options

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
