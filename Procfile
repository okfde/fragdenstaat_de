web: DJANGO_SETTINGS_MODULE=fragdenstaat_de.settings gunicorn froide.wsgi
worker: celery -A froide worker -Q emailfetch,celery -B -l INFO
