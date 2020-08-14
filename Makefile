export DJANGO_SETTINGS_MODULE=fragdenstaat_de.settings.test
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=default

test:
	flake8 froide
	python manage.py test tests --keepdb

testci:
	python manage.py test tests --keepdb
