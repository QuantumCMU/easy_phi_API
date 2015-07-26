#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

# TODO: add meaningful long description
# First, write it to Readme.md
# then, copy it here and document in process to transfer all Readme updates
long_description = "Software for test measurement equipment platform."

# options reference: https://docs.python.org/2/distutils/
setup(
    name="easy_phi",
    packages=['easy_phi', 'scripts'],
    version="0.3",
    license="GPL v3.0",
    description='Easy Phi project web application',
    long_description=long_description,
    author='Team Quantum',
    author_email='shadeless@ya.ru',
    url='https://github.com/QuantumCMU/easy_phi_API',
    download_url='http://github.com/QuantumCMU/easy_phi_API/archive/master.zip',
    keywords=['measurement equipment', 'SCPI', 'udev', 'TMC', 'VISA'],
    classifiers=(  # see https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 1 - Planning",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: "
        "Interface Engine/Protocol Translator",
    ),
    entry_points = {
        'console_scripts': ['easy_phi = easy_phi.app:main']
    },
    data_files=[
        ('/etc', ['scripts/easy_phi.conf']),
        ('/etc/udev/rules.d', ['scripts/99-easy_phi-modules.rules']),
        ('/etc/easy_phi', ['scripts/modules_conf_patches.conf',
                           'scripts/widgets.conf']),
    ],
    package_data={
        'scripts': ['*'],
        'easy_phi': ['templates/*.html',
                     'static/js/*.js',
                     'static/css/*.css',
                     'static/css/themes/redmond/*.css',
                     'static/css/themes/redmond/images/*.png',
                     'static/css/themes/smoothness/*.css',
                     'static/css/themes/smoothness/images/*.png',
                     'static/favicon.ico'
                     'static/robots.txt'
                     ],
    },
    install_requires=[
        'tornado',
        'pyudev',
        'pyserial',
        'dicttoxml',
        'pkgtools',
        'pip',
        'keyring'
    ],
    # TODO: add unit tests
)
