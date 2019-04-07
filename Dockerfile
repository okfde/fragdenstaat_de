FROM python:3.5

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE fragdenstaat_de.settings.development
ENV DJANGO_CONFIGURATION Dev
ENV NODE_ENV development

RUN apt-get update -y && apt-get install -y build-essential binutils libproj-dev libpq-dev gdal-bin libgeos-dev libgeos-c1v5 python-gdal

RUN curl -sL https://deb.nodesource.com/setup_9.x | bash - && apt-get update -y && apt-get install -y nodejs

COPY requirements-dev.txt /code/
COPY requirements.txt /code/
RUN pip install -r /code/requirements-dev.txt
COPY froide /code/froide
RUN pip uninstall -y froide && pip install -e /code/froide/

COPY yarn.lock /code/
COPY package.json /code/

RUN cd /code/ && npm install -g yarn && yarn install

COPY .babelrc /code/
COPY manage.py /code/
COPY webpack.config.js /code/
COPY Procfile.dev /code/

WORKDIR /code/
EXPOSE 8000
