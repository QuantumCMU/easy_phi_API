from distutils.core import setup

from easy_phi import VERSION, LICENSE, PROJECT

#options reference: https://docs.python.org/2/distutils/
setup(
    name = PROJECT,
    packages = [PROJECT],
    version = VERSION,
    license = LICENSE,
    description = 'Easy Phi project web application',
    long_description=open('README.md').read(),

    author = 'Team Quantum',
    author_email = 'shadeless@ya.ru',
    url = 'https://github.com/QuantumCMU/easy_phi_API',
    download_url = 'https://github.com/QuantumCMU/easy_phi_API/tarball/'+VERSION,
    keywords = ['measurement equipment', 'SCPI', 'udev', 'TMC', 'VISA'],
    classifiers=( #see https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 1 - Planning",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator",
    ),
    data_files=[
        ('/etc', ['scripts/easy_phi.conf']),
        ('/etc/udev/rules.d', ['scripts/99-easy_phi-modules.rules']),
    ],
    requires = [
        'tornado',
    ],
)
