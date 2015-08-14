# -*- coding: utf-8 -*-

from tornado.test.util import unittest

from easy_phi import hislip


class HiSLIPMessageTest(unittest.TestCase):

    def test_parameter_manipulations(self):

        message = hislip.HiSLIPMessage(0, parameter=0xff8844ff)
        self.assertEqual(message.parameter_lword, 0x44ff)
        self.assertEqual(message.parameter_uword, 0xff88)

        message.parameter_lword = 0xaadd
        self.assertEqual(message.parameter, 0xff88aadd)
        message.parameter_uword = 0x88ff
        self.assertEqual(message.parameter, 0x88ffaadd)
