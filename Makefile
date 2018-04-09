COMPOSE=docker-compose
DEVDOCKER=$(COMPOSE) run --rm backend

all: setup migrate web

services:
	$(COMPOSE) up -d db elasticsearch

shell: services
	$(DEVDOCKER) /bin/bash

migrate: build services
	$(DEVDOCKER) python manage.py migrate --noinput

web: services
	$(COMPOSE) up backend

stop:
	$(COMPOSE) down
	$(COMPOSE) rm -f

clean:
	rm -rf dist build .eggs
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +

setup:
	./devsetup.sh
	$(COMPOSE) build

build:
	$(COMPOSE) stop backend
	$(DEVDOCKER) npm run build

.PHONY: build
