export DJANGO_SETTINGS_MODULE=fragdenstaat_de.settings.test
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=ignore,default:::fragdenstaat_de

test:
	flake8 fragdenstaat_de
	python manage.py test tests --keepdb

testci:
	python manage.py test tests --keepdb
