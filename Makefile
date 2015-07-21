clean:
	find -type f -name *.pyc -delete
	rm -rf dist
	rm -rf build

test:
	python -m easy_phi.tests.run_tests

regression_test:
	python -m unittest easy_phi.tests.regression_test

run:
	python easy_phi/app.py

package:
	make clean
	#python setup.py register #need only for the first time
	python setup.py sdist upload

testpackage:
	python setup.py upload -r https://testpypi.python.org/pypi

docs:
	mkdocs

install:
	python setup.py install

install_dev:
	[ -h "/etc/udev/rules.d/99-easy_phi-modules.rules" ] || [ -e "/etc/udev/rules.d/99-easy_phi-modules.rules" ] || ln -s `pwd`/scripts/99-easy_phi-modules.rules /etc/udev/rules.d/99-easy_phi-modules.rules
	[ -h "/etc/easy_phi.conf" ] || [ -e "/etc/easy_phi.conf" ] || ln -s `pwd`/scripts/easy_phi.conf /etc/easy_phi.conf
	[ -d "/etc/easy_phi" ] || mkdir /etc/easy_phi
	[ -h "/etc/easy_phi/widgets.conf" ] || [ -e "/etc/easy_phi/widgets.conf" ] || ln -s `pwd`/scripts/widgets.conf /etc/easy_phi/widgets.conf
	[ -h "/etc/easy_phi/modules_conf_patches.conf" ] || [ -e "/etc/easy_phi/modules_conf_patches.conf" ] || ln -s `pwd`/scripts/modules_conf_patches.conf /etc/easy_phi/modules_conf_patches.conf

uninstall:
	rm -rf /usr/local/lib/python2.7/dist-packages/easy_phi-0.*
	rm -rf /var/www/html/easy_phi
	rm -rf /etc/easy_phi
	rm /etc/easy_phi.conf
	rm /etc/udev/rules.d/99-easy_phi-modules.rules
