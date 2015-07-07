#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

from easy_phi import VERSION, LICENSE, PROJECT

rq_fh = open('requirements.txt', 'r')
reqs = [line.split("#", 1)[0].strip() for line in rq_fh.read().split("\n")
        if line.split("#", 1)[0].strip()]

# options reference: https://docs.python.org/2/distutils/
setup(
    name=PROJECT,
    packages=[PROJECT],
    version=VERSION,
    license=LICENSE,
    description='Easy Phi project web application',
    long_description=open('README.md').read(),

    author='Team Quantum',
    author_email='shadeless@ya.ru',
    url='https://github.com/QuantumCMU/easy_phi_API',
    download_url='https://github.com/QuantumCMU/easy_phi_API/tarball/'+VERSION,
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
    requires=reqs,
    # TODO: add unit tests
)
