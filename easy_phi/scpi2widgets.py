#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility library to convert list of supported SCPI commands to HTML widgets
"""

import logging
import ConfigParser

from tornado.options import options, define


define("widgets_conf_path", default='/etc/easy_phi/widgets.conf')

# This is a ConfigParser object for lazy initialization in scpi2widgets()
_widgets_storage = None


def scpi2widgets(configuration):
    """ Return javascript widgets to create UI corresponding to supported
    SCPI commands.

    :param configuration: list (iterable) of supported SCPI commands
            list of commands can be obtained from module object by
    :param slot_id: integer to be used to substitute {slot_id} in widgets
    :param container: jQuery selector for DOM element to place widget in
    :return: list of widgets, i.e. chunks of javascript creating web UI
    """
    global _widgets_storage

    def valid_section(section):
        return _widgets_storage.has_option(section, 'scpi') and \
            _widgets_storage.has_option(section, 'widget')

    if _widgets_storage is None:  # lazy initialization
        _widgets_storage = ConfigParser.ConfigParser()
        _widgets_storage.read(options.widgets_conf_path)
        if 'scpi' in _widgets_storage.defaults() or \
            'widget' in _widgets_storage.defaults():
            logging.warning("widgets configuration file has default values "
                             "for scpi or widget (it should not)")
        for section in _widgets_storage.sections():
            if not valid_section(section):
                logging.warning("Section {0} does not define "
                                "scpi or widget attribute".format(section))
                pass

    module_conf = set(configuration)
    widgets = []

    # ConfigParser orders section backwards, so have to reverse again
    for section in reversed(_widgets_storage.sections()):
        if not valid_section:
            continue
        widget_conf = _widgets_storage.get(section, 'scpi').split("\n")
        if module_conf.issuperset(widget_conf):
            widget = _widgets_storage.get(section, 'widget')
            widgets.append(widget)
            module_conf = module_conf.difference(widget_conf)

    return widgets
