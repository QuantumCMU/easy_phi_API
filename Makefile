clean:
	find -type f -name *.pyc -delete
	rm -rf dist

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

uninstall:
	rm -rf /var/www/html/easy_phi
	rm -rf /etc/easy_phi
	rm /etc/easy_phi.conf
	rm /etc/udev/rules.d/99-easy_phi-modules.rules
