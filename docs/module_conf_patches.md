
Problem
-------
not all equipment is willing to tell us supported commands
========

Easy Phi generates web interface of a module basing on list of supported SCPI commands.
Usually this list can be acquired by issuing SYSTem:HELP? command, but in many cases
it is not implemented. Besides a wide range of legacy hardware whose developers were
to sloppy to implement full support of SCPI standard, in some cases it is not possible
to put all handlers into small memory of micro controller, or time to market is more
important than full standard compatibility. So, let's accept it as fact that there is
an equipment which doesn't tell us what SCPI commands it support.


Solution
--------
... store configuration patches in separate file
=============

In many cases we know set of supported commands, e.g. from printed manual, its just
can not be extracted from equipment itself. In this case we might put list of commands
into special file and tell system to use this list for this piece of equipment. I.e.
we just mapping of equipment to list of supported scpi commands.

TODO: add path to default configuration file

Problem #2
-----------
equipment name is not unique identifier
=========

In industry, manufacturers of serial equipment usually provide unique name for the
equipment, e.g. "ACME oscilloscope ACOS-2319". However, it is in industry world where
every piece of equipment produced in a large series and there is a lot of attention to
details. In a research world custom piece of equipment might be created just for a
single experiment, simply by adding handlers to a standard template. Many deverlopers
don't even care to change default name in the template, making device detection a
challenging task.

Solution #2
-----------
custom rules
===============

First solution to this problem is to provide more flexible configuration, i.e. not only
by name but also by vendor id, serial number etc. Hopefully more flexible rules allow
to catch the difference between multiple pieces of ad-hoc equipment.

TODO: add example of configuration
    