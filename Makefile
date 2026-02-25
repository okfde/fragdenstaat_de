export DJANGO_SETTINGS_MODULE=fragdenstaat_de.settings.test
export DJANGO_CONFIGURATION=Test
export PYTHONWARNINGS=ignore,default:::fragdenstaat_de

test:
	ruff check
	pytest --reuse-db

testci:
	coverage run --branch -m pytest --reuse-db
	coverage report

backend_dependencies: pyproject.toml
	uv pip compile -o requirements.txt pyproject.toml -p 3.12
	uv pip compile -o requirements-dev.txt --extra dev pyproject.toml -p 3.12
	uv pip compile -o requirements-production.txt --extra production pyproject.toml -p 3.12

frontend_dependencies:
	./devsetup.sh upgrade_frontend_repos

dependencies: backend_dependencies frontend_dependencies

commitdependencies: dependencies
	git add requirements.txt requirements-dev.txt requirements-production.txt pnpm-lock.yaml
	git commit -m "Update dependencies"

messagesde:
	python manage.py extendedmakemessages -l de --ignore public --ignore froide-env --ignore node_modules --ignore htmlcov --ignore src --add-location file --no-wrap --sort-output
