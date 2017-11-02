FROM python:3.5

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE fragdenstaat_de.settings.development
ENV DJANGO_CONFIGURATION Dev

# Copy early, will be overwritten by volume mapping anyway
COPY . /code/
RUN pip install -r /code/requirements-dev.txt
RUN pip uninstall -y froide && pip install -e /code/froide/

WORKDIR /code/

EXPOSE 8000
