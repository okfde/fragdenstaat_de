export DJANGO_SETTINGS_MODULE=fragdenstaat_de.settings.test
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=ignore,default:::fragdenstaat_de

test:
	ruff check
	pytest --reuse-db

testci:
	coverage run --branch -m pytest --reuse-db
	coverage report

requirements: pyproject.toml
	uv pip compile -o requirements.txt pyproject.toml
	uv pip compile -o requirements-dev.txt --extra dev pyproject.toml
	uv pip compile -o requirements-production.txt --extra production pyproject.toml

dependencies:
	./devsetup.sh upgrade_frontend_repos

sync_frontend_deps: requirements dependencies

messagesde:
	python manage.py makemessages -l de --ignore public --ignore froide-env --ignore node_modules --ignore htmlcov --ignore src --add-location file
