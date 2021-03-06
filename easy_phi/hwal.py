#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Implementation of classes representing different classes of equipment
This module also contains implementation of system-wide commands supported
by broadcast module. These are special SCPI commands returning platform-levevl
information about the system, such as number of available slots.
"""

import serial
import datetime

from tornado.options import options, define
import tornado.gen
import tornado.concurrent
import tornado.iostream
import tornado.locks

from easy_phi import mod_conf_patch
from easy_phi import utils

define("serial_port_timeout", default=2)
define("serial_port_baudrate", default=9600)


class AbstractMeasurementModule(object):
    """ Abstract class for representation of test measurement equipment
    It should not be used directly but rather serve as a reference for
    different module types subclasses
    """

    name = "Abstract module"
    lock = None

    def __init__(self, device, data_callback=None):
        """ Initialize module object with pyudev.Device object """
        self.device = device
        self.lock = tornado.locks.Lock()

    @staticmethod
    def is_instance(device):
        """ Check if the device supported by this module
        :param device: pyudev.Device instance
        :return: boolean
        """
        return False

    def scpi(self, command):
        """Send SCPI command to device
        Note that all subclusses are responsible of handling self.lock to
        prevent concurrent operations
        """
        raise NotImplementedError

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


class SerialStream(tornado.iostream.BaseIOStream):
    """ Adaption of tornado.iostream.IOStream from sockets to searial port

    Before changing anything here, please look carefully at code of classes
    mentioned in this article:
    http://golubenco.org/understanding-the-code-inside-tornado-the-asynchronous-web-server-powering-friendfeed.html
    """
    _timeout_handler = None
    _data_callback = None
    serial = None

    # note that self.buffer is different from self._read_buffer
    # we'll use streaming callback, so _read_buffer will remain empty
    buffer = ''

    def __init__(self, port, data_callback=None, *args, **kwargs):
        self.serial = port
        self.serial.timeout = 0
        super(SerialStream, self).__init__(*args, **kwargs)
        self._data_callback = data_callback

    def start(self, delimiter="\r"):
        """This class represents data communication with serial device.
        Major problem we have is there is no indication for end of transmission
        in serial communication. Command that takes too long to process, failed
        or disconnected equipment on serial port, or command that does not
        produce any output look the same for us. To overcome this, we listen for
        all the data coming from port. If we have a pending command waiting for
        data, we assume it is a response and return it. If we get data without
        command, it might indicate one of the situations:
            - previous command timed out and we already returned empty string
            - previous command generates constant stream of data
            -
        """
        self._read_delimiter = delimiter
        self.read_until_close(streaming_callback=self._handle_chunk)

    def _handle_chunk(self, chunk):
        self.buffer += chunk
        if self.buffer.endswith(self._read_delimiter):
            # buffer might catch extra newline at the beginning from previous
            # output, if command was implemented sloppy or \r\n are in wrong
            # order. Also, it has a newline at the end
            self.buffer = self.buffer.strip()

            if self._read_future is not None:  # called readline()
                self._resolve_future()
            elif self._data_callback is not None:
                self._data_callback(self.buffer)
            self.buffer = ''

    def _resolve_future(self):
        """ Force complete read, e.g. by timeout
        - set future result
        - clear buffer and self._read_future
        - remove timeout (if set)
        """
        assert self._read_future is not None, "can't complete without future"
        assert self._timeout_handler is not None, "no timeout handler"
        self._read_future.set_result(self.buffer)
        self._read_future = None
        # remove timeout
        self.io_loop.remove_timeout(self._timeout_handler)
        self._timeout_handler = None

    def readline(self, timeout=options.serial_port_timeout):
        """ Helper method to read a single line with timeout """
        self._read_future = tornado.concurrent.TracebackFuture()
        self._timeout_handler = self.io_loop.add_timeout(
            datetime.timedelta(seconds=timeout),
            self._resolve_future)
        return self._read_future

    def fileno(self):
        return self.serial.fileno()

    def close_fd(self):
        self.serial.close()

    def write_to_fd(self, data):
        return self.serial.write(data)

    def read_from_fd(self):
        # will return empty string if no data is ready
        try:
            res = self.serial.read(self.read_chunk_size)
        except serial.SerialException:
            # module was extracted during read. Ignore, module will be removed
            # anyway
            res = None
        return res or None

    def connect(self, *args, **kwargs):
        """ Trap to check that no legacy code uses this method """
        raise NotImplementedError


class CDCModule(AbstractMeasurementModule):
    """New style module with serial interface only, or truly serial device """
    stream = None
    serial = None
    _name_scpi_command = "*IDN?"

    def __init__(self, device, data_callback=None):
        """ This class instantiated by pyudev listener from hwconf.py
        Listener is run on a separate thread and should not block HTTP requests
        :param device: pyudev.Device instance
               data_callback: will be called after reception of data chunk. It
                    was introduced to support generation commands. For example,
                    this callback can push data to websocket for continuous
                    read
        :return: None
        """
        assert self.is_instance(device)
        super(CDCModule, self).__init__(device, data_callback=data_callback)
        self.serial = serial.Serial(
            device['DEVNAME'],
            options.serial_port_baudrate,
            timeout=options.serial_port_timeout)
        # Note that this is a blocking operation. Fortunately, it is executed
        # on a different thread since module class instantiated by udev listener
        # later SerialStream will force port to non-blocking mode (timeout=0)
        try:
            self.serial.write(self._name_scpi_command+"\n")
            self.name = self.serial.readline()
        except serial.SerialException:
            # module was extracted before name was read. It is ok, udev will
            # notify about extraction soon and module will be destroyed
            return

        self.stream = SerialStream(self.serial, data_callback=data_callback)
        self.stream.start()

    @staticmethod
    def is_instance(device):
        """ Check if the device supported by this module
        :param device: pyudev.Device instance
        :return: boolean
        """
        return device.get('ID_USB_DRIVER') == 'cdc_acm' and 'DEVNAME' in device

    @tornado.gen.coroutine
    def scpi(self, command):
        """Send SCPI command to the device
        :param command: string with SCPI command. It is not validated to be
                valid SCPI command,  it is your responsibility
        :return string with command response.
        """
        # First, acquire lock on the port. It is necessary to prevent concurrent
        # requests from the same user / api token
        with (yield self.lock.acquire()):
            yield self.stream.write(command.strip() + "\n")
            result = yield self.stream.readline()
        # At this point read future is resolved, due to timeout or end of
        # output, so it is safe to release lock
        raise tornado.gen.Return(result)


class LegacyEasyPhiModule(CDCModule):
    """ Legacy modules implemented for the first version of Easy Phi platform.
    These modules used composite USB interface and had SD card on board.
    Main difference from "normal" CDC modules is name handling. In first
    versions of firmware *IDN? request returned the same name for all modules.
    Actual device name was returned by SYSTEM:NAME? command
    """
    _name_scpi_command = "SYSTem:NAME?"

    @staticmethod
    def is_instance(device):
        return CDCModule.is_instance(device) \
            and device['ID_VENDOR'] == 'Easy-phi'


class USBTMCModule(AbstractMeasurementModule):
    """Class to represent USB TMC device """
    def __init__(self, device, data_callback=None):
        # TODO: implement non blocking read/write in a similar to CDC way
        super(USBTMCModule, self).__init__(device, data_callback=data_callback)

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
    """ Fake module to broadcast messages to all connected equipment.
    This module also implements few special system wide commands, returning
    platform level configuration
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
                # systemwide commands do not accept arguments
                return callback()

        response = None
        for module in reversed(self.modules[1:]):
            if isinstance(module, AbstractMeasurementModule):
                response = module.scpi(command)

        if response is None:
            # if at least one module present, it will be empty string even if
            # no response was received.
            return "**No modules connected"

        return response

    def get_configuration(self):
        """ Return list of supported commands
        """
        conf = super(BroadcastModule, self).get_configuration()
        conf += [cmd[0] for cmd in self.platformwide_commands()
                 if cmd[0] not in conf]
        return conf

# Please note that it is not conventional __all__ defined in __init__.py,
# it contains list of classes instead of strings.
# hwconf.py iterates these modules and calls static method is_instance()
# to see if device is supported by the system
module_classes = [
    LegacyEasyPhiModule,
    CDCModule,
    USBTMCModule
]
