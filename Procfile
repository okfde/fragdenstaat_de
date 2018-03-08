web: DJANGO_SETTINGS_MODULE=fragdenstaat_de.settings.development gunicorn froide.wsgi
worker: celery -A froide worker -Q emailfetch,celery,email -B -l INFO
