# -*- coding: utf-8 -*-

from tornado.test.util import unittest

from easy_phi import utils


class FormatConversionsTest(unittest.TestCase):

    def test_format_conversion_string(self):

        response_text, ctype = \
            utils.format_conversion("Hello world", 'plain')
        self.assertEqual(u'Hello world', response_text)

        response_text, ctype = \
            utils.format_conversion("Hello world", 'xml')
        self.assertEqual('<?xml version="1.0" encoding="UTF-8" ?><root>'
                         '<item type="str">Hello world</item></root>',
                         response_text)

        response_text, ctype = \
            utils.format_conversion("Hello world", 'json')
        self.assertEqual('"Hello world"', response_text)

    def test_format_conversion_list(self):
        response_text, ctype = \
            utils.format_conversion(['one', 1, None], 'plain')
        self.assertMultiLineEqual(response_text, "one\n1\nNone")

        response_text, ctype = \
            utils.format_conversion(['one', 1, None], 'xml')
        self.assertEqual('<?xml version="1.0" encoding="UTF-8" ?><root>'
                         '<item type="str">one</item><item type="int">1</item>'
                         '<item type="null"></item></root>', response_text)

        response_text, ctype = \
            utils.format_conversion(['one', 1, None], 'json')
        self.assertEqual('["one", 1, null]', response_text)

    def test_format_conversion_dict(self):
        # Since dict is not ordered (except plain text), we have to test
        # both possible orders of keys
        response_text, ctype = \
            utils.format_conversion({'one': 1, 2: None}, 'plain')
        self.assertEqual("2: None\none: 1", response_text)

        # dicttoxml does not support integer indices
        response_text, ctype = \
            utils.format_conversion({'one': 1, '45': None}, 'xml')
        self.assertTrue('<?xml version="1.0" encoding="UTF-8" ?><root>'
                        '<n45 type="null"></n45><one type="int">1</one>'
                        '</root>' == response_text or
                        '<?xml version="1.0" encoding="UTF-8" ?><root>'
                        '<one type="int">1</one><n45 type="null"></n45>'
                        '</root>' == response_text)

        response_text, ctype = \
            utils.format_conversion({'one': 1, 2: None}, 'json')
        self.assertTrue('{"2": null, "one": 1}' == response_text or
                        '{"one": 1, "2": null}' == response_text)

    def test_format_conversion_ctype(self):

        response_text, ctype = \
            utils.format_conversion("Hello world", 'plain')
        self.assertEqual("text/plain", ctype)

        response_text, ctype = \
            utils.format_conversion("Hello world", 'xml')
        self.assertEqual("application/xml", ctype)

        response_text, ctype = \
            utils.format_conversion("Hello world", 'json')
        self.assertEqual("application/json", ctype)
