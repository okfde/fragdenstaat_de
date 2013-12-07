# -*- coding: utf-8 -*-
import os

from froide.settings import Base, ThemeBase, German


class FragDenStaatBase(German, ThemeBase, Base):

    gettext = lambda s: s
    LANGUAGES = (
        ('de', gettext('German')),
    )

    FROIDE_THEME = 'fragdenstaat_de.theme'

    @property
    def INSTALLED_APPS(self):
        installed = super(FragDenStaatBase, self).INSTALLED_APPS
        installed += [
            'foiidea',
            'celery_haystack',
            'djcelery_email',
            'djangosecure',
        ]
        return installed

    @property
    def GEOIP_PATH(self):
        return os.path.join(super(FragDenStaatBase, self).PROJECT_ROOT, '..', 'data')

    MIDDLEWARE_CLASSES = [
        'django.contrib.sessions.middleware.SessionMiddleware',
        'djangosecure.middleware.SecurityMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.common.CommonMiddleware',
    ]

    CACHES = {
        'default': {
            'LOCATION': 'unique-snowflake',
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
        }
    }

    ########## Debug ###########

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
            'URL': 'http://127.0.0.1:8983/solr/fragdenstaat'
        }
    }
    HAYSTACK_SIGNAL_PROCESSOR = 'celery_haystack.signals.CelerySignalProcessor'

    SITE_NAME = "Frag den Staat"
    SITE_EMAIL = "info@fragdenstaat.de"
    SITE_URL = 'http://localhost:8000'

    SECRET_URLS = {
        "admin": "admin",
    }

    DEFAULT_FROM_EMAIL = 'info@fragdenstaat.de'
    EMAIL_SUBJECT_PREFIX = '[AdminFragDenStaat] '

    EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
    CELERY_EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


class Dev(FragDenStaatBase):
    pass


try:
    from .local_settings import *  # noqa
except ImportError:
    pass
