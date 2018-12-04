# FragDenStaat.de

This repository contains the theming for
[FragDenStaat.de](https://fragdenstaat.de) - the German instance of [Froide](https://github.com/okfde/froide).


## Development environment

FragDenStaat.de is a Django app with a PostgreSQL+PostGIS database and elasticsearch 2.4.6.
[There is a production deployment ansible configuration for details.](https://github.com/okfde/fragdenstaat.de-ansible). If you want an easy  start, please use the below instructions with Docker (note that this is for convenience and that the actual deployment does not use Docker at the moment).

If you do not want to use Docker, you can install this like any Django project with dependencies and services.

### Docker setup

You need [docker](https://www.docker.com/community-edition) and [docker-compose](https://docs.docker.com/compose/). Make sure Docker is running and use the following command:

```
make all
```

This will download the necessary docker images and build a docker image and start a python web server and a webpack watch server for building JS/CSS (includes live reload). The current directory is mounted inside the container, changes to templates are picked up and the frontend files should be rebuild.

The following make targets are available:

- `make setup` - updates local froide source and builds docker image
- `make services` - starts services in the background
- `make migrate` - runs database migrations
- `make stop` - stops all services
- `make build` - build frontend files for production and commit
- `make shell` - opens shell in web app container


## License

Froide and fragdenstaat_de are licensed under the AGPL License.

Some folders contain an attributions.txt with more information about the copyright holders for files in this specific folder.
