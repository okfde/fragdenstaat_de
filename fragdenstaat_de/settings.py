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
            'django.contrib.redirects',
            'django.contrib.flatpages'
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
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
        'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
        'froide.account.middleware.AcceptNewTermsMiddleware',
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
    CELERY_EMAIL_TASK_CONFIG = {
        'max_retries': None,
        'ignore_result': False,
        'acks_late': True,
        'store_errors_even_if_ignored': True
    }

    @property
    def FROIDE_CONFIG(self):
        config = super(FragDenStaatBase, self).FROIDE_CONFIG
        config.update(dict(
            create_new_publicbody=False,
            publicbody_empty=True,
            user_can_hide_web=True,
            public_body_officials_public=True,
            public_body_officials_email_public=False,
            default_law=2,
            doc_conversion_binary="/usr/bin/libreoffice",
            dryrun=False,
            dryrun_domain="fragdenstaat.stefanwehrmeyer.com",
            allow_pseudonym=True,
            api_activated=True,
            search_engine_query='http://www.google.de/search?as_q=%(query)s&as_epq=&as_oq=&as_eq=&hl=en&lr=&cr=&as_ft=i&as_filetype=&as_qdr=all&as_occt=any&as_dt=i&as_sitesearch=%(domain)s&as_rights=&safe=images',
            show_public_body_employee_name=False,
            greetings=[rec(u"Sehr geehrt(er? (?:Herr|Frau)(?: ?Dr\.?)?(?: ?Prof\.?)? .*)")],
            closings=[rec(u"[Mm]it( den)? (freundlichen|vielen|besten) Gr\xfc\xdfen,?"), rec("Hochachtungsvoll,?"), rec('i\. ?A\.'), rec('[iI]m Auftrag')]
        ))
        return config


class Dev(FragDenStaatBase):
    pass


try:
    from .local_settings import *  # noqa
except ImportError:
    pass
