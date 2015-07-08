# -*- coding: utf-8 -*-

import tempfile

from tornado.test.util import unittest
from tornado.options import options

from easy_phi import mod_conf_patch


class BasicConfParserTest(unittest.TestCase):
    conf = None  # keep link to NamedTempFile or it will be deleted

    def setUp(self):
        self.device = {
            u'DEVLINKS': u'/dev/serial/by-path/pci-0000:00:14.0-usb-0:2:1.0',
            u'DEVNAME': u'/dev/ttyACM1',
            u'DEVPATH': u'/devices/pci0000:00/0000:00:14.0э'
                        u'/usb3/3-2/3-2:1.0/tty/ttyACM1',
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
            u'USEC_INITIALIZED': u'255013737'
        }

        confpatch = tempfile.NamedTemporaryFile()
        confpatch.write("""[DEFAULT]
scpi = *IDN?

[Easy Phi high speed Logic gate]
ID_VENDOR = Easy-phi
ID_SERIAL_SHORT = 123123123123
scpi = CONFigure:OUT1? (OR|AND|IN1|IN2)
        CONFigure:OUT2? (OR|AND|IN1|IN2)
        CONFigure:OUT3? (OR|AND|IN1|IN2)
        CONFigure:OUT4? (OR|AND|IN1|IN2)
        """)
        confpatch.flush()

        options.modules_conf_patches_path = confpatch.name
        self.conf = confpatch

        mod_conf_patch._init_config()

    def test_init_config(self):
        self.assertEqual(mod_conf_patch.legacy_commands.strip(), "*IDN?")
        self.assertIsInstance(mod_conf_patch.legacy_configs, list)

    def test_configuration_match(self):
        self.assertTrue(mod_conf_patch.configuration_match(
            self.device,
            [('ID_VENDOR', 'Easy-phi'), ('ID_SERIAL_SHORT', '123123123123')]
        ))

        # match by single property
        self.assertTrue(mod_conf_patch.configuration_match(
            self.device,
            [('ID_VENDOR', 'Easy-phi')]
        ))

        device = self.device.copy()
        device['ID_VENDOR'] = 'ACME'

        # mismatch by one property
        self.assertFalse(mod_conf_patch.configuration_match(
            device,
            [('ID_VENDOR', 'Easy-phi'), ('ID_SERIAL_SHORT', '123123123123')]
        ))

        # mismatch by single property
        self.assertFalse(mod_conf_patch.configuration_match(
            device,
            [('ID_SERIAL_SHORT', '0000000')]
        ))

        # if desired property not in device properties, don't count it as match
        self.assertFalse(mod_conf_patch.configuration_match(
            {},
            [('ID_SERIAL_SHORT', '123123123123')]
        ))

    def test_get_configuration_patch(self):
        self.assertSequenceEqual(
            mod_conf_patch.get_configuration_patch(self.device),
            [
                "*IDN?",
                "CONFigure:OUT1? (OR|AND|IN1|IN2)",
                "CONFigure:OUT2? (OR|AND|IN1|IN2)",
                "CONFigure:OUT3? (OR|AND|IN1|IN2)",
                "CONFigure:OUT4? (OR|AND|IN1|IN2)"
            ]
        )

        self.assertSequenceEqual(
            mod_conf_patch.get_configuration_patch({}),
            ["*IDN?"]
        )

