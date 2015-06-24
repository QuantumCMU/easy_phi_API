clean:
	find -type f -name *.pyc -delete
	rm -rf dist

test:
	python -m easy_phi.tests.run_tests

run:
	easy_phi/app.py

package:
	make clean
	#python setup.py register #need only for the first time
	python setup.py sdist upload

testpackage:
	python setup.py upload -r https://testpypi.python.org/pypi

docs:
	mkdocs
