#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import dicttoxml
from xml.dom.minidom import parseString

from tornado.options import options, define

import hwconf
import auth

DEFAULT_FORMAT = 'json'
define("default_format", default=DEFAULT_FORMAT)


def format_conversion(res, fmt=DEFAULT_FORMAT, callback=''):
    if fmt == 'xml':
        ctype = 'application/xml'
        response_text = dicttoxml.dicttoxml(res)
        if options.debug:  # prettify XML for better debugging
            response_text = parseString(response_text).toprettyxml()

    elif fmt == 'plain':  # Plain text
        ctype = 'text/plain'
        if isinstance(res, dict):
            response_text = "\n".join((u"{0}: {1}".format(*item)
                                       for item in res.items()))
        elif isinstance(res, list):
            response_text = "\n".join(map(unicode, res))
        else:
            response_text = unicode(res)
    else:  # fmt == 'json':
        json_kwargs = {
            'sort_keys': True,
            'indent': 4,
            'separators': (',', ': ')
        } if options.debug else {}

        ctype = 'application/json'
        response_text = json.dumps(res, **json_kwargs)
        if callback:  # JSONP support, for cross-domain static JS API
            response_text = ''.join((callback, '(', response_text, ')'))

    return response_text, ctype


def multiformat(func):
    """ Decorator for Tornado web request handlers to format response
    into xml/json/plain by the GET['format'] parameter
    """

    def wrapper(self):
        fmt = self.get_argument('format', options.default_format)
        res = func(self)
        if res is None:  # generic handler, using self.write()
            return
        response_text, ctype = format_conversion(
            res, fmt, callback=self.get_argument('callback', ''))
        self.set_header('content-type', ctype)
        self.finish(response_text)

    return wrapper


def api_auth(func):
    def wrapper(self):
        # TODO: use HTTP auth basic instead of get parameters
        api_token = self.get_argument("key", '')
        if not auth.validate_api_token(api_token):
            self.set_status(401)
            return {'error': "Invalid api key. Please check if you're"
                             " authenticated in the system"}
        self.api_token = api_token
        return func(self)

    return wrapper


def require_slot(allow_bcast=True):
    """ Class wrapper for API handlers to validate required 'slot' parameter
    :param allow_bcast: boolean, either to accept slot=0 or not
    """
    def cls_decorator(handler):
        def method_decorator(func):
            def wrapper(self):
                err = ''
                slot = self.get_argument('slot', '')
                if slot == '':
                    err = 'Missing slot number. Add ?slot=N to URL'
                else:
                    try:
                        self.slot = int(slot)
                    except ValueError:
                        err = 'Slot number must be an integer'
                    else:
                        max_slot = len(hwconf.modules) - 1
                        min_slot = 0 if allow_bcast else 1
                        if not min_slot <= self.slot <= max_slot:
                            err = 'Invalid slot number. Number in range ' + \
                                  '{0}..{1} expected'.format(min_slot, max_slot)
                        elif hwconf.modules[self.slot] is None:
                            err = 'Selected slot is empty'

                if err:
                    self.set_status(400)
                    return {'error': err}
                else:
                    return func(self)
            return wrapper

        for method in ('get', 'post', 'put', 'head', 'delete'):
            setattr(handler, method, method_decorator(getattr(handler, method)))

        return handler
    return cls_decorator
