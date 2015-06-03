#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides functions to obtain hardware configuration and keep it up to date.

"""

import pyudev
import hwal
from tornado.options import options

callbacks = [
    # hardware configuration change listener will call these methods
    # it is necessary to send updates to websockets
]

# device #0 represents broadcast
modules = [None for i in range(options.slots + 1)]
modules[0] = hwal.BroadcastModule(modules)

_context = pyudev.Context()


def get_rack_slot(device):
    global modules  # Ugly, I know. Let me know if there is a better way

    # first, check if device is already represented in modules
    for i, module in enumerate(modules):
        if module.device == device:
            return i

    # if it is not in the list, match it with USB ports of the rack
    # TODO: get usb ports list from config file (command line option)
    slot = 1

    # if device is neither in modules list nor port is associated with rack slot, assign to first free slot
    if not 1 <= slot <= options.slots:
        for i in range(options.slots + 1, len(modules)):
            if modules[i] is None:
                return i
        slot = len(modules)
        modules += [None]
    return slot


def hwconf_update():
    """Check connected devices and refresh modules list.
    Usually this method is called upon system startup or restart to
    restore current hardware configuration
    """
    for device in _context.list_devices():
        for module_class in hwal.__all__:
            if module_class.is_instance(device):
                modules[get_rack_slot(device)] = module_class(device)
                break


def hwconf_listener(action, device):
    """udev events listener to update modules list dynamically
    This method shall not be used directly. It is only for purpose of integration with pyudev
    """

    module_class = None
    for mc in hwal.__all__:
        if mc.is_instance(device):
            module_class = mc
            break
    if module_class is None:
        return

    rack_slot = get_rack_slot(device)
    added = action not in ('remove', 'offline')
    modules[rack_slot] = module_class(device) if added else None

    for callback in callbacks:
        if callable(callback):
            callback(added, rack_slot)

# for asynchronous hw configuration monitoring reference see
# https://pyudev.readthedocs.org/en/latest/guide.html#asynchronous-monitoring
monitor = pyudev.Monitor.from_netlink(_context)
observer = pyudev.MonitorObserver(monitor, hwconf_listener)

# update hardware configuration on start
observer.start()
hwconf_update()


def stop():
    """tear down udev listener for clean exit"""
    observer.stop()
