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

    :param configuration: list (iterable) of SCPI commands supported by module.
            This list can be obtained by module.get_configuration
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

    module_conf = set(configuration)
    widgets = []

    for section in _widgets_storage.sections():
        if not valid_section:
            continue
        widget_conf = _widgets_storage.get(section, 'scpi').split("\n")
        if module_conf.issuperset(widget_conf):
            widget = _widgets_storage.get(section, 'widget')
            if widget:  # commands in ignore list have empty widgets
                widgets.append(widget)
            module_conf = module_conf.difference(widget_conf)

    if 'default_widget' in _widgets_storage.defaults():
        widgets.append(_widgets_storage.defaults()['default_widget'])

    return widgets
