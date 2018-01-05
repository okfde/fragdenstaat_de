import os

import django_cache_url

from .base import FragDenStaatBase


def env(key, default=None):
    return os.environ.get(key, default)


class FragDenStaat(FragDenStaatBase):
    DEBUG = False
    TEMPLATE_DEBUG = False
    CELERY_TASK_ALWAYS_EAGER = False
    CELERY_SEND_TASK_ERROR_EMAILS = True

    ADMINS = (('FragDenStaat.de', 'mail@fragdenstaat.de'),)
    MANAGERS = (('FragDenStaat.de', 'mail@fragdenstaat.de'),)

    SECURE_FRAME_DENY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True

    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

    DATA_UPLOAD_MAX_MEMORY_SIZE = 15728640
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

    USE_X_ACCEL_REDIRECT = True
    X_ACCEL_REDIRECT_PREFIX = '/protected'

    ALLOWED_HOSTS = ('fragdenstaat.de',)
    ALLOWED_REDIRECT_HOSTS = ('fragdenstaat.de', 'sanktionsfrei.de',)

    CACHES = {'default': django_cache_url.config()}

    CELERY_EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': env('DATABASE_NAME'),
            'OPTIONS': {},
            'HOST': env('DATABASE_HOST'),
            'USER': env('DATABASE_USER'),
            'PASSWORD': env('DATABASE_PASSWORD'),
            'PORT': ''
        }
    }

    @property
    def TEMPLATES(self):
        TEMP = super(FragDenStaat, self).TEMPLATES
        TEMP[0]['OPTIONS']['debug'] = False
        loaders = TEMP[0]['OPTIONS']['loaders']
        TEMP[0]['OPTIONS']['loaders'] = [
            ('django.template.loaders.cached.Loader', loaders)
        ]
        return TEMP

    CELERY_BROKER_URL = env('DJANGO_CELERY_BROKER_URL')

    CUSTOM_AUTH_USER_MODEL_DB = 'auth_user'

    DEFAULT_FROM_EMAIL = 'info@fragdenstaat.de'
    EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
    # EMAIL_HOST
    # EMAIL_HOST_PASSWORD
    # EMAIL_HOST_USER
    EMAIL_SUBJECT_PREFIX = '[AdminFragDenStaat] '
    EMAIL_USE_TLS = True
    EMAIL_PORT = 25
    FOI_EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    # FOI_EMAIL_ACCOUNT_NAME
    # FOI_EMAIL_ACCOUNT_PASSWORD
    FOI_EMAIL_DOMAIN = ['fragdenstaat.de', 'echtemail.de']
    FOI_EMAIL_FIXED_FROM_ADDRESS = False
    FOI_EMAIL_FUNC = None
    # FOI_EMAIL_HOST
    # FOI_EMAIL_HOST_FROM
    # FOI_EMAIL_HOST_IMAP
    # FOI_EMAIL_HOST_PASSWORD
    # FOI_EMAIL_HOST_USER
    FOI_EMAIL_PORT = 25
    FOI_EMAIL_PORT_IMAP = 143
    FOI_EMAIL_USE_SSL = False
    FOI_EMAIL_USE_TLS = True
    FOI_MEDIA_PATH = 'foi'

    GEOIP_PATH = env('DJANGO_GEOIP_PATH')

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'froide.helper.elasticsearch.FroideElasticsearch2SearchEngine',
            'URL': 'http://127.0.0.1:9200/',
            'INDEX_NAME': 'fragdenstaat_de',
        }
    }
    HAYSTACK_SIGNAL_PROCESSOR = 'celery_haystack.signals.CelerySignalProcessor'

    LOGGING = {
        'loggers': {
            'froide': {
                'level': 'INFO',
                'propagate': True,
                'handlers': ['normal']
            },
            'sentry.errors': {
                'handlers': ['normal'],
                'propagate': False,
                'level': 'DEBUG'
            },
            'django.request': {
                'level': 'ERROR',
                'propagate': True,
                'handlers': ['normal']
            },
            'raven': {
                'handlers': ['normal'],
                'propagate': False,
                'level': 'DEBUG'
            }
        },
        'disable_existing_loggers': False,
        'handlers': {
            'normal': {
                'filename': os.path.join(env('DJANGO_LOG_DIR'), 'froide.log'),
                'class': 'logging.FileHandler',
                'level': 'INFO'
            },
            'mail_admins': {
                'class': 'django.utils.log.AdminEmailHandler',
                'filters': ['require_debug_false'],
                'level': 'ERROR'
            }
        },
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            }
        },
        'version': 1,
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse'
            }
        },
        'root': {
            'handlers': ['normal'],
            'level': 'WARNING'
        }
    }
    MANAGERS = (('FragDenStaat.de', 'mail@fragdenstaat.de'),)
    MEDIA_ROOT = env('DJANGO_MEDIA_ROOT')
    MEDIA_URL = '/files/'
    FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o2750
    FILE_UPLOAD_PERMISSIONS = 0o640

    MIDDLEWARE = [
        'django.middleware.security.SecurityMiddleware',
        'froide.helper.middleware.XForwardedForMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'fragdenstaat_de.theme.ilf_middleware.CsrfViewIlfMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
        'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
        'froide.account.middleware.AcceptNewTermsMiddleware',
    ]

    SECRET_KEY = env('DJANGO_SECRET_KEY')
    SECRET_URLS = {
        'admin': env('DJANGO_SECRET_URL_ADMIN')
    }

    RAVEN_CONFIG = {}
    if env('DJANGO_SENTRY_DSN') is not None:
        RAVEN_CONFIG['dsn'] = env('DJANGO_SENTRY_DSN')

    SERVER_EMAIL = 'info@fragdenstaat.de'

    SITE_EMAIL = 'info@fragdenstaat.de'
    SITE_ID = 1
    SITE_NAME = 'Frag den Staat'
    SITE_URL = 'https://fragdenstaat.de'

    TASTYPIE_DEFAULT_FORMATS = ['json']
