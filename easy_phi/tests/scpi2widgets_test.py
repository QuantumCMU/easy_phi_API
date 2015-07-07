# -*- coding: utf-8 -*-

import tempfile

from tornado.test.util import unittest
from tornado.options import options

from easy_phi import scpi2widgets


class BasicWidgetsTest(unittest.TestCase):
    reset_widget = "reset widget"
    sysname_widget = "system name widget"
    container = "#blablah"
    conf = None  # link to NamedTempFile to prevent deletion

    def setUp(self):
        widgets_conf = tempfile.NamedTemporaryFile()
        widgets_conf.write("""[DEFAULT]

[RESET]
scpi = *RST
widget = {reset_widget}

[System name]
scpi = SYSTem:NAME?
widget = {sysname_widget}\n""".format(reset_widget=self.reset_widget,
                                      sysname_widget=self.sysname_widget))
        widgets_conf.flush()
        self.conf = widgets_conf

        options.widgets_conf_path = widgets_conf.name

    def test_scpi2widgets(self):
        widgets = scpi2widgets.scpi2widgets([])
        self.assertIsInstance(widgets, list)
        self.assertSequenceEqual(
            widgets, [],
            "Empty module configuration resulted in non-empty widgets. "
            "Received widgets: {widgets}".format(widgets=widgets)
        )

        widgets = scpi2widgets.scpi2widgets(["*RST"])
        self.assertIsInstance(widgets, list)
        self.assertSequenceEqual(
            widgets, [self.reset_widget],
            "Reset command in configuration resulted in wrong widget."
            "Expected: [{reset_widget}], Response: {widgets}".format(
                widgets=widgets, reset_widget=self.reset_widget)
        )

        widgets = scpi2widgets.scpi2widgets(["SYSTem:NAME?"])
        self.assertIsInstance(widgets, list)
        self.assertSequenceEqual(
            widgets, [self.sysname_widget],
            "System name command in configuration resulted in wrong widget.\n"
            "Expected: [{system_widget}], Response: {widgets}".format(
                system_widget=self.sysname_widget, widgets=widgets)
        )

        widgets = scpi2widgets.scpi2widgets(["SYSTem:NAME?", "*RST"])
        self.assertIsInstance(widgets, list)
        self.assertSequenceEqual(
            widgets, [self.reset_widget, self.sysname_widget])
