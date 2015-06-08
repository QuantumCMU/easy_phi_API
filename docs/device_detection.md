
General
===

Unfortunately, we have no assumptions about device vendor and device id. For example, legacy modules detected as:
> Bus 003 Device 007: ID 03eb:2424 Atmel Corp.
where 0x03eb is Atmel vendor id, i.e. manufacturer of controller chip.


udev rules
=====

udev is a system component responsible for mounting devices from sysfs into user space (/dev/*). It uses set of rules
for creating device nodes, to ensure proper access mode, node name etc. These rules are stored in two places,
`/lib/udev/rules.d/` and `/etc/udev/rules.d`. The former one is a set of default system rules, the latter is user
defined rules. As a rule of thumb you should not edit these files directly but put another one to to override the
existing rule.

Depending on the system used and usb connection topology, detected modules may be assigned different properties and
match different udev rules. Sometimes it results in improper mode set or node name. To override existing setting, you
need it to be executed before default rule, so new rule shoud have lower number. If you want to add new property or
create additional symlink using existing properties, you need to add new rule with higher number.

For example, by default on Ubuntu system tty and serial devices are affected by these rules:

    /lib/udev/rules.d/50-udev-default.rules
    /lib/udev/rules.d/60-persistent-serial.rules
    /lib/udev/rules.d/77-mm-usb-serial-adapters-greylist.rules

First file defines default mode for tty devices. To override that, your new rule should have number higher than 50.
For example, your new rule may be placed in a file `/etc/udev/rules.d/99-easy_phi-modules.rules`.

*Note1:* you can not use softlinks for udev rules, you have to put actual file into rules directory.

*Note2:* on some Linux distributions (Ubuntu 14.04) you need to tear down ENV{ID_MM_CANDIDATE} in udev rules to make
serial port accessible

There is also set of rules for usb_modeswitch in `/lib/udev/rules.d/40-usb_modeswitch.rules` you can use as a reference
for composite device (legacy) modules.


Legacy modules
====

Sample output of SCPI commands from logic gate module:
> *IDN?
    CTU FEE, TEST SCPI INSTRUMENT TSI3225, v1.0\r\n
> SYSTem:NAME?
    High Speed Logic Gate\r
> SYSTem:SN?
    0x0000\r
> SYSTem:VERsion?
    v1.0\r\n
> SYSTem:TYPE?
    High Speed Logic Gate\r
> SYSTem:DESC?
    High Speed Logic Gate\r
> SYST:blah #unsupported command
    **ERROR: -113, "Undefined header"\r\n
> SYST:ERR?
    -113, "Undefined header"\r\n
> SYST:ERR:NEXT?
    0, "No error"\r\n

Output of $ udevadm info:
udevadm info --name=/dev/ttyACM1 --query=all

    P: /devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0/tty/ttyACM1
    N: ttyACM1
    S: serial/by-id/usb-Easy-phi_Template_Board_123123123123-if00
    S: serial/by-path/pci-0000:00:14.0-usb-0:1:1.0
    E: DEVLINKS=/dev/serial/by-id/usb-Easy-phi_Template_Board_123123123123-if00 /dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0
    E: DEVNAME=/dev/ttyACM1
    E: DEVPATH=/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0/tty/ttyACM1
    E: ID_BUS=usb
    E: ID_MM_CANDIDATE=1
    E: ID_MODEL=Template_Board
    E: ID_MODEL_ENC=Template\x20Board
    E: ID_MODEL_ID=2424
    E: ID_PATH=pci-0000:00:14.0-usb-0:1:1.0
    E: ID_PATH_TAG=pci-0000_00_14_0-usb-0_1_1_0
    E: ID_REVISION=0100
    E: ID_SERIAL=Easy-phi_Template_Board_123123123123
    E: ID_SERIAL_SHORT=123123123123
    E: ID_TYPE=generic
    E: ID_USB_DRIVER=cdc_acm
    E: ID_USB_INTERFACES=:020201:0a0000:080650:
    E: ID_USB_INTERFACE_NUM=00
    E: ID_VENDOR=Easy-phi
    E: ID_VENDOR_ENC=Easy-phi
    E: ID_VENDOR_FROM_DATABASE=Atmel Corp.
    E: ID_VENDOR_ID=03eb
    E: MAJOR=166
    E: MINOR=1
    E: SUBSYSTEM=tty
    E: USEC_INITIALIZED=953101815

pyudev.Device dict:

     {u'DEVLINKS': u'/dev/serial/by-id/usb-Easy-phi_Template_Board_123123123123-if00 /dev/serial/by-path/pci-0000:00:14.0-usb-0:2:1.0',
     u'DEVNAME': u'/dev/ttyACM1',
     u'DEVPATH': u'/devices/pci0000:00/0000:00:14.0/usb3/3-2/3-2:1.0/tty/ttyACM1',
     u'ID_BUS': u'usb',
     u'ID_MM_CANDIDATE': u'1',
     u'ID_MODEL': u'Template_Board',
     u'ID_MODEL_ENC': u'Template\\x20Board',
     u'ID_MODEL_ID': u'2424',
     u'ID_PATH': u'pci-0000:00:14.0-usb-0:2:1.0',
     u'ID_PATH_TAG': u'pci-0000_00_14_0-usb-0_2_1_0',
     u'ID_REVISION': u'0100',
     u'ID_SERIAL': u'Easy-phi_Template_Board_123123123123',
     u'ID_SERIAL_SHORT': u'123123123123',
     u'ID_TYPE': u'generic',
     u'ID_USB_DRIVER': u'cdc_acm',
     u'ID_USB_INTERFACES': u':020201:0a0000:080650:',
     u'ID_USB_INTERFACE_NUM': u'00',
     u'ID_VENDOR': u'Easy-phi',
     u'ID_VENDOR_ENC': u'Easy-phi',
     u'ID_VENDOR_FROM_DATABASE': u'Atmel Corp.',
     u'ID_VENDOR_ID': u'03eb',
     u'MAJOR': u'166',
     u'MINOR': u'1',
     u'SUBSYSTEM': u'tty',
     u'USEC_INITIALIZED': u'255013737'}

New modules (usb serial devices)
=====


USB-TMC equipment
=====