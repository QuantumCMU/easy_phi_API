#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import dicttoxml
from xml.dom.minidom import parseString

import pkgtools.pypi


def format_conversion(chunk, fmt, debug=False):
    if fmt == 'xml':
        ctype = 'application/xml'
        chunk = dicttoxml.dicttoxml(chunk)
        if debug:  # prettify XML for better debugging
            chunk = parseString(chunk).toprettyxml()

    elif fmt == 'plain':  # Plain text
        ctype = 'text/plain'
        if isinstance(chunk, dict):
            chunk = "\n".join((u"{0}: {1}".format(key, chunk[key])
                               for key in sorted(chunk.keys())))
        elif isinstance(chunk, list):
            chunk = "\n".join(map(unicode, chunk))
        else:
            chunk = unicode(chunk)

    elif fmt == 'json':
        ctype = 'application/json'
        chunk = json.dumps(chunk, sort_keys=debug, indent=debug*4 or None,
                           separators=(', ', ': '))
    else:
        raise ValueError("fmt is supposed to be xml, plain or json")

    return chunk, ctype


def scpi_equivalent(command, canonical):
    # TODO: add docstring, documentation, unittest
    command = command.strip().split(" ", 1)[0]
    canonical = canonical.strip().split(" ", 1)[0]

    # i is index of current char in command, j is index for canonical form
    i = j = 0
    # TODO: actually implement this method
    # TODO: add support for default command
    while True:
        if command == canonical:
            return True
        break

    return False


def parse_scpi_command(raw_str):
    # TODO: add docstring, documentation, unittest
    chunks = raw_str.split(" ", 2)
    cmd = chunks[0]
    arg = "" or len(chunks) > 1 and chunks[1]
    remainder = "" or len(chunks) > 2 and chunks
    return cmd, arg, remainder


def get_latest_pypi_version():
    """Get version of latest release available on PyPi
    This function is used by system upgrade function
    """
    from easy_phi import __project__ as proj
    p = pkgtools.pypi.PyPIXmlRpc()
    releases = p.package_releases(proj)
    if releases and len(releases)>0:
        return releases[0]
