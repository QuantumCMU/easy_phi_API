#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides functions to obtain hardware configuration and keep it
up to date.
"""

import pyudev

from tornado.options import define, options

from easy_phi import hwal

define('ports', default=[])

callbacks = [
    # hardware configuration change listener will call these methods.
    # It is necessary to send updates to websockets
]

modules = [None]
# device #0 represents broadcast
modules[0] = hwal.BroadcastModule(modules)

_context = pyudev.Context()


def get_rack_slot(device):
    """ Return rack slot by device object. If usb device hierarchy is not
    associated with any rack slot, dynamically add a new slot or reuse first
    free slot from dynamically created before. By default system is configured
    for 0 slots so everything is created dynamically.
    :param device: pyudev.Device object.
    :return integer slot number, 1...~20. Slot 0 is reserved for broadcasting
    """
    global modules  # Ugly, I know. Let me know if there is a better way

    # first, check if device is already represented in modules
    # pyudev.Device does not guarantee uniqueness, so we have to ensure if
    # device isn't already associated with some slot
    for i, module in enumerate(modules):
        if module is not None and module.device == device:
            return i

    # if it is not in the list, match it with USB ports of the rack
    if device['ID_PATH'] in options.ports:
        return options.ports.index(device['ID_PATH']) + 1

    # if device is neither in modules list nor port is associated with rack
    # slot, assign to first free slot. It might happen in standalone mode, or
    # if a supported device connected directly to a board inside rack, i.e.
    # it is not not a typical scenario for commercially distributed systems.
    for i in range(len(options.ports) + 1, len(modules)):
        if modules[i] is None:
            return i
    slot = len(modules)
    modules += [None]
    return slot


def hwconf_update():
    """ Check connected devices and refresh modules list.
    Usually this method is called upon system startup or restart to
    restore current hardware configuration
    """
    for device in _context.list_devices():
        for module_class in hwal.module_classes:
            if module_class.is_instance(device):
                slot = get_rack_slot(device)
                modules[slot] = module_class(device)
                break


def hwconf_listener(action, device):
    """ udev events listener to update modules list dynamically
    This method shall not be used directly. It is only for purpose of
    integration with pyudev
    """

    module_class = None
    for mc in hwal.module_classes:
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
# observer is a subclass of threading.Thread
observer = pyudev.MonitorObserver(monitor, hwconf_listener)


def start():
    """ update hardware configuration on start and install udev listener """
    global modules
    modules += [None] * len(options.ports)
    if not observer.is_alive():  # start() called twice before stop()
        observer.start()
    hwconf_update()


def stop():
    """tear down udev listener for clean exit"""
    observer.stop()
