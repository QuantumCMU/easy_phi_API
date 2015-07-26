#!/usr/bin/env python
# -*- coding: utf-8 -*-

import serial
import threading

from tornado.options import options, define

from easy_phi import mod_conf_patch
from easy_phi import utils

define("serial_port_timeout", default=2)
define("serial_port_baudrate", default=3000000)


def lock(func):
    """decorator to prevent concurrent execution of some function
    This decorator should be used to wrap calls to devices to evade overlapping
    commands from different requests
    For SCPI supporting devices, same can be achieved by using  SCPI commands
    *WAI, *OPC? or *STB?, but lock will result in lower latency
    """
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'lock'):
            self._lock = threading.Lock()
            self.is_locked = lambda x: x.lock.locked()
        self._lock.acquire()
        retval = func(self, *args, **kwargs)
        self._lock.release()
        return retval
    return wrapper


class AbsractModuleMetaclass(type):
    def __new__(mcs, name, bases, dct):
        mod_class = super(AbsractModuleMetaclass, mcs).__new__(
            mcs, name, bases, dct)
        if hasattr(mod_class, 'scpi') and mod_class.scpi == mcs.scpi:
            setattr(mod_class, 'scpi', lock(mod_class.scpi))
        return mod_class

# will be applied to all classes in this module
# it is not ok to do it in AbstractMeasurementModule because @lock
# will be applied by all classes in inheritance chain
__metaclass__ = AbsractModuleMetaclass


class AbstractMeasurementModule(object):
    """ Abstract class for representation of test measurement equipment
    It should not be used directly but rather serve as a reference for
    different module types subclasses
    """

    name = "Abstract module"

    def __init__(self, device):
        """ Initialize module object with pyudev.Device object """
        self.device = device

    @staticmethod
    def is_instance(device):
        """ Check if the device supported by this module
        :param device: pyudev.Device instance
        :return: boolean
        """
        return False

    def scpi(self, command):
        """Send SCPI command to device"""
        return "OK"

    def get_configuration(self):
        """ Get module configuration.
        Configuration format is still under discussion, but likely it will
        be represented by hierarchy of available SCPI commands """
        # TODO: use SYSTem:HELP? and SYSTem:HELP:SYNTax? <command header>
        return mod_conf_patch.get_configuration_patch(self.device)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name.decode()


class CDCModule(AbstractMeasurementModule):
    """New style module with serial interface only, or truly serial device
    There are 12 legacy modules without support for configuration command.
    These modules shall be detected by id and return hardcoded configuration.
    """
    def __init__(self, device):
        assert self.is_instance(device)
        self.serial = serial.Serial(
            device['DEVNAME'],
            options.serial_port_baudrate,
            timeout=options.serial_port_timeout
        )
        self.name = str(self.scpi("*IDN?")).rstrip()  # remove newline
        super(CDCModule, self).__init__(device)

    @staticmethod
    def is_instance(device):
        """ Check if the device supported by this module
        :param device: pyudev.Device instance
        :return: boolean
        """
        return device.get('ID_USB_DRIVER') == 'cdc_acm' and 'DEVNAME' in device

    def scpi(self, command):
        """Send SCPI command to the device
        :param command: string with SCPI command. It is not validated to be
                valid SCPI command,  it is your responsibility
        :return string with command response.
        """
        # sanitize input:
        command = command.strip() + "\n"
        self.serial.write(command)
        output = self.serial.readline()
        if output.startswith('**'):
            # TODO: handle errorrs
            pass
        # some equipment/commands leave newline \r symbol at the end
        return output.strip()


class LegacyEasyPhiModule(CDCModule):
    """ Legacy modules implemented for the first version of platform.
    Main difference from "normal" CDC modules is name handling. In first
    versions of firmware *IDN? request returned the same name for all modules.
    Actual device name was returned by SYSTEM:NAME? command
    """
    def __init__(self, device):
        super(LegacyEasyPhiModule, self).__init__(device)
        self.name = str(self.scpi("SYSTEM:NAME?")).strip()

    @staticmethod
    def is_instance(device):
        return CDCModule.is_instance(device) \
            and device['ID_VENDOR'] == 'Easy-phi'


class USBTMCModule(AbstractMeasurementModule):
    """Class to represent USB TMC device
    Only generic configuration will be returned. USB-TMC devices are supported
    to provide VISA access, so generation of appropriate web interface is not
    critical. It is possible however to return predefined configuration from
    some kind of device database
    """
    def __init__(self, device):
        # TODO: implement this method
        super(USBTMCModule, self).__init__(device)

    @staticmethod
    def is_instance(device):
        """ Check if the device supported by this module
        :param device: pyudev.Device instance
        :return: boolean
        """
        # TODO: check actual usb-tmc device properties and update
        return device.get('ID_USB_DRIVER') == 'usbtmc'

    def scpi(self, command):
        # TODO: write actual implementation
        return "OK"


class BroadcastModule(AbstractMeasurementModule):
    """ Fake module to broadcast messages to all modules connected to platform.
    """

    name = "Broadcast dummy module"

    def platformwide_commands(self):
        return [
            ("RAck:Size?", lambda: len(options.ports)),
            ("SYSTem:NUMber:SLots?", lambda: len(self.modules)),
            ("SYSTem:VERSion?", lambda: options.sw_version),
        ]

    def __init__(self, modules):
        self.modules = modules
        super(BroadcastModule, self).__init__(None)

    def scpi(self, command):
        """Send SCPI command to all connected modules
        :param command: string with SCPI command. It is not validated to be
                valid SCPI command, it is your responsibility
        :return always "OK".
        """
        for canonical, callback in self.platformwide_commands():
            if utils.scpi_equivalent(command, canonical):
                return callback()

        response = None
        for module in reversed(self.modules[1:]):
            if isinstance(module, AbstractMeasurementModule):
                response = module.scpi(command)

        return response

    def get_configuration(self):
        conf = super(BroadcastModule, self).get_configuration()
        conf += [command for command, callback in self.platformwide_commands()]
        return conf

# Please note that it is not conventional __all__ defined in __init__.py,
# it contains list of classes instead of strings.
# hwconf.py iterates these modules and calls static method is_instance()
# to see if device is supported by the system
__all__ = module_classes = [
    LegacyEasyPhiModule,
    CDCModule,
    USBTMCModule
]
