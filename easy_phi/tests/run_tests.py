# -*- coding: utf-8 -*-

import tornado.testing
from tornado.test.util import unittest

TEST_MODULES = [
    'easy_phi.tests.handlers_test',
    'easy_phi.tests.mod_conf_patch_test',
    'easy_phi.tests.utils_test',
    'easy_phi.tests.scpi2widgets_test',
]


def all():
    return unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)

if __name__ == '__main__':
    tornado.testing.main()
