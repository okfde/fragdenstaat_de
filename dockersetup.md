First, clone the repository and enter:

```bash
git clone https://github.com/okfde/fragdenstaat_de
cd fragdenstaat_de
```

There are currently two options for a setup with Docker:

1. Only Database + Elasticsearch (See README.md)

Use this when developing locally with Python/pnpm installed on your machine and setting up a virtual environment, but want to avoid setting up PostgreSQL and Elasticsearch manually.

2. Full Docker setup

This full setup builds the Docker image installing the necessary dependencies, compiling messages and making an initial migration.
Vite and Django serve from different containers.

Make sure to have a local_settings.py file in /fragdenstaat_de/settings/. You can copy the example file from /fragdenstaat_de/settings/local_settings.py.example.

Run the setup script

```bash
./devsetuph.sh dockerized
```
This clones the froide repositories and builds the docker image with all the dependencies and links, mimicking the setup for a virtual environment, just inside the container.

Please note that the image can take over ten minutes to build and because of Vite incompatibilities, the containers run in "host" network mode, which may cause conflicts if those ports are already in use. It could be necessary to adjust the settings in Docker Desktop to allow the use of network host mode.

Then start the containers with
```bash
docker compose up -d
```

Django will be listening on http://localhost:8000, Vite on http://localhost:5173

### Initial setup

devsetup.sh automatically runs `python manage.py migrate --skip-checks` after build. However, you may still need to:

1. Create a superuser
``` bash
docker compose exec -it django python manage.py createsuperuser
```

2. Load initial data
``` bash
docker compose exec django python manage.py loaddata tests/fixtures/cms.json
```

3. Create search index
``` bash
docker compose exec django python manage.py search_index --create
docker compose exec django python manage.py search_index --populate
```

For more convenient access you can use the container's shell:
``` bash
docker compose exec -it django bash
```
