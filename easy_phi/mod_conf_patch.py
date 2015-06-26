#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Helper module to handle reading/matching configuration

This module implements configuration patches for module devices (i.e. get list
of supported SCPI commands
https://en.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments
"""

import ConfigParser

from tornado.options import define, options

define('modules_conf_patches_path',
       default='/etc/easy_phi/modules_conf_patches.conf')

# legacy_configs holds list of tuples (device_config, module_config)
#
# module_config is a list of supported SCPI commands separated by newline
# Example:
# CONFigure:OUT1?
# CONFigure:OUT1 (OR|AND|IN1|IN2)
# CONFigure:OUT2?
# CONFigure:OUT2 (OR|AND|IN1|IN2)
#
# device config is a list of tuples (property, value)
# property is a name of udev device property, see device_detection.md
# Example:
# [('ID_VENDOR', 'Easy-phi'), ('ID_SERIAL_SHORT','123123123123')]
legacy_configs = None
# legacy_commands is a list of commands mandatory for all modules
# it is defined in section [Default] of the configuration file
# example of such commands is *RST, *IDN? and *WAI
legacy_commands = ''


def configuration_match(device, device_config):
    """ This method compares pyudev device to stored configuration.
    It is necessary to return stored configuration for SCPI devices which
    do not return list of available SCPI commands by SYSTem:HELP?
    Device configuration in this case will be obtained from list of hardcoded
    configurations, usually configuration file or separate Python module.
    :param device: pyudev device instance
    :param device_config: list of (name, value) device properties to match
    :return: boolean, True if device matches configuration.
    """
    return all(key in device and device[key] == value
               for key, value in device_config)


def _init_config():
    """ Initialization of module configuration patches
    This method is created for lazy initialization
    :return: None
    """
    global legacy_configs, legacy_commands
    confpatch_parser = ConfigParser.ConfigParser()
    confpatch_parser.read(options.modules_conf_patches_path)
    legacy_configs = []
    for section in confpatch_parser.sections():
        module_config = confpatch_parser.get(section, 'scpi')
        # key.upper() is necessary because pyudev.Device keys are uppercase
        # and we want keys in config patches file to be case insensitive
        device_config = [(key.upper(), value) for key, value in
                         confpatch_parser.items(section) if key != 'scpi']
        legacy_configs.append((device_config, module_config))
    default_section = confpatch_parser.defaults()
    legacy_commands = default_section.get('scpi', '')


def get_configuration_patch(device):
    """ Return module configuration from configuration file
    This method will return generic conf if no configuration matched

    :param device:
    :return: list of supported commands
    """
    global legacy_configs, legacy_commands
    if legacy_configs is None:
        _init_config()

    commands = legacy_commands
    if device is not None:  # pseudo modules, e.g. broadcast
        for device_config, module_config in legacy_configs:
            if configuration_match(device, device_config):
                if not commands.endswith("\n"):
                    commands += "\n"
                commands += module_config
                break

    # final step - remove blank lines if any
    return [command for command in commands.split("\n") if command]


if __name__ == '__main__':
    _init_config()
