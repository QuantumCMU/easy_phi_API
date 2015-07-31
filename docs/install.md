
CentOS / RHEL
=========

Tested on CentOS 6

    # to get tornado.speedups, you need to install python-devel
    yum install python-devel
    # Pip is installed from epel repo. If it is not installed, you can do it
    # by yum install epel-release
    yum install python-pip
    # or, by yum install python-setuptools; easy_install pip
    # you python-pip
    yum install libudev python-pip
    # easy_install won't let to install console scritps. Use pip
    pip install easy_phi
    # Centos comes with outdated certifi version, need to update
    easy_install --upgrade certifi
    

Debian/Ubuntu
====

Tested on Ubuntu Server 14.04 and Debian Wheezy

    # tornado speedups compiled at install, so we need python-dev
    apt-get install python-dev
    # depending on distribution version, libudev can be either libudev0 or libudev1
    # installing libudev-dev will pull up the right version as a dependency
    apt-get install python-pip libudev-dev
    pip install easy_phi
    
Slackware
=====

Tested on Slackware 14.1

    # libudev is installed by default
    # install pip
    wget ftp://208.94.238.115/14.1/python/pysetuptools.tar.gz
    tar -zxvf pysetuptools.tar.gz
    cd pysetuptools
    # address from pysetuptools.info
    wget https://pypi.python.org/packages/source/s/setuptools/setuptools-18.0.1.tar.gz
    chmod +x pysetuptools.SlackBuild
    ./pysetuptools.SlackBuild
    pkgtool # select pysetuptools package from /tmp
    # finally, it is almost a normal Linux
    pip install easy_phi

    
BSD
=====

It won't work because of libudev support (there is no one).
Since there is no other reasonse for system not to run on BSD, we might consider
making a fallback mechanism for detecting changes in hardware configuration.
    
    
OpenWrt
======

As of now, libudev does not come in OpenWrt distribution. In theory, if you 
compile libudev for your platform, you can install the system. This configuration
was not tested though.

First, you need to add repositories to /etc/opkg.conf. Following is file content,
not commands to execute:

    src pack http://downloads.openwrt.org/barrier_breaker/14.07/x86/generic/packages/packages
    src base http://downloads.openwrt.org/barrier_breaker/14.07/x86/generic/packages/base
    src luci http://downloads.openwrt.org/barrier_breaker/14.07/x86/generic/packages/luci
    src oldp http://downloads.openwrt.org/barrier_breaker/14.07/x86/generic/packages/oldpackages
    src mgmt http://downloads.openwrt.org/barrier_breaker/14.07/x86/generic/packages/management
    src rout http://downloads.openwrt.org/barrier_breaker/14.07/x86/generic/packages/routing
    src phon http://downloads.openwrt.org/barrier_breaker/14.07/x86/generic/packages/telephony

Then, run:

    opkg update
    opkg install python
    opkg install distribute
    # opkg will fail to download packages from https without python-openssl
    opkg install python-openssl
    easy_install pip
    pip install easy_phi
    
