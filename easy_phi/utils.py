#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import dicttoxml
from xml.dom.minidom import parseString


def format_conversion(chunk, fmt, debug=False):
    if fmt == 'xml':
        ctype = 'application/xml'
        chunk = dicttoxml.dicttoxml(chunk)
        if debug:  # prettify XML for better debugging
            chunk = parseString(chunk).toprettyxml()

    elif fmt == 'plain':  # Plain text
        ctype = 'text/plain'
        if isinstance(chunk, dict):
            chunk = "\n".join((u"{0}: {1}".format(*item)
                               for item in chunk.items()))
        elif isinstance(chunk, list):
            chunk = "\n".join(map(unicode, chunk))
        else:
            chunk = unicode(chunk)
    elif fmt == 'json':
        json_kwargs = {
            'sort_keys': True,
            'indent': 4,
            'separators': (',', ': ')
        } if debug else {}

        ctype = 'application/json'
        chunk = json.dumps(chunk, **json_kwargs)
    else:
        raise ValueError("fmt is supposed to be xml, plain or json")

    return chunk, ctype
