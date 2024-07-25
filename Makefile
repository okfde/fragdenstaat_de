export DJANGO_SETTINGS_MODULE=fragdenstaat_de.settings.test
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=ignore,default:::fragdenstaat_de

test:
	ruff check
	pytest --reuse-db

testci:
	coverage run --branch -m pytest --reuse-db
	coverage report

requirements: requirements.in requirements-dev.in requirements-production.in
	uv pip compile requirements.in -o requirements.txt
	uv pip compile requirements-dev.in -o requirements-dev.txt
	uv pip compile requirements-production.in -o requirements-production.txt

messagesde:
	python manage.py makemessages -l de --ignore public --ignore froide-env --ignore node_modules --ignore htmlcov --ignore src --add-location file
