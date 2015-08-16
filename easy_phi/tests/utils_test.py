# -*- coding: utf-8 -*-

""" Unit tests for easy_phi.utils module """

from tornado.test.util import unittest

from easy_phi import utils


class FormatConversionsTest(unittest.TestCase):
    """ Test utility function for format conversion on various data types"""

    def test_format_conversion_string(self):
        """ Test string format conversion """
        response_text = utils.format_conversion("Hello world", 'plain')[0]
        self.assertEqual(u'Hello world', response_text)

        response_text = utils.format_conversion("Hello world", 'json')[0]
        self.assertEqual('"Hello world"', response_text)

    def test_format_conversion_list(self):
        """ Test list format conversion """
        response_text = utils.format_conversion(['one', 1, None], 'plain')[0]
        self.assertMultiLineEqual(response_text, "one\n1\nNone")

        response_text = utils.format_conversion(['one', 1, None], 'json')[0]
        self.assertEqual('["one", 1, null]', response_text)

    def test_format_conversion_dict(self):
        """ Test dict format conversion """
        # Since dict is not ordered (except plain text), we have to test
        # both possible orders of keys
        response_text, ctype = \
            utils.format_conversion({'one': 1, 2: None}, 'plain')
        self.assertEqual("2: None\none: 1", response_text)
        self.assertEqual("text/plain", ctype)

        response_text, ctype = \
            utils.format_conversion({'one': 1, 2: None}, 'json')
        self.assertTrue('{"2": null, "one": 1}' == response_text or
                        '{"one": 1, "2": null}' == response_text)
        self.assertEqual("application/json", ctype)


class UpdateUtilFunctionTest(unittest.TestCase):
    """ Test function used by software update """

    def test_get_latest_pypi_version(self):
        """ Sanity check version on pypi is not higher than development one"""
        from easy_phi import __version__ as version
        release = utils.get_latest_pypi_version()
        self.assertGreaterEqual(version, release)
