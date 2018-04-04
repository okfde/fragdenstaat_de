FROM python:3.5

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE fragdenstaat_de.settings.development
ENV DJANGO_CONFIGURATION Dev

RUN apt-get update -y && apt-get install -y build-essential binutils libproj-dev libpq-dev gdal-bin libgeos-dev libgeos-c1 python-gdal

RUN curl -sL https://deb.nodesource.com/setup_9.x | bash - && apt-get update -y && apt-get install -y nodejs


# Copy early, will be overwritten by volume mapping anyway
COPY requirements-dev.txt /code/
COPY requirements.txt /code/
RUN pip install -r /code/requirements-dev.txt
COPY froide /code/froide
RUN pip uninstall -y froide && pip install -e /code/froide/

COPY package.json /code/
# COPY yarn.lock /code/
RUN cd /code/ && npm install && npm rebuild node-sass --force

COPY . /code/
WORKDIR /code/

EXPOSE 8000
