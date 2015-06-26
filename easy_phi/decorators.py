#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hwconf
import auth


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
