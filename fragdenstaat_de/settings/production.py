import os

import django_cache_url

import raven

from .base import FragDenStaatBase, env


class FragDenStaat(FragDenStaatBase):
    DEBUG = False
    TEMPLATE_DEBUG = False
    CELERY_TASK_ALWAYS_EAGER = False
    CELERY_TASK_EAGER_PROPAGATES = False
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
    STATIC_URL = 'https://static.frag-den-staat.de/static/'

    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

    USE_X_ACCEL_REDIRECT = True
    X_ACCEL_REDIRECT_PREFIX = '/protected'

    ALLOWED_HOSTS = ('fragdenstaat.de', 'media.frag-den-staat.de', 'testserver')
    ALLOWED_REDIRECT_HOSTS = ('fragdenstaat.de', 'sanktionsfrei.de',)

    PAYMENT_HOST = 'fragdenstaat.de'
    PAYMENT_USES_SSL = True
    PAYMENT_VARIANTS = {
        'creditcard': ('froide_payment.provider.StripeIntentProvider', {
            'public_key': env('STRIPE_PUBLIC_KEY'),
            'secret_key': env('STRIPE_PRIVATE_KEY'),
            'signing_secret': env('STRIPE_SIGNING_KEY'),
        }),
        'sepa': ('froide_payment.provider.StripeSourceProvider', {
            'public_key': env('STRIPE_PUBLIC_KEY'),
            'secret_key': env('STRIPE_PRIVATE_KEY'),
        })
    }

    CACHES = {'default': django_cache_url.config()}

    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
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

    DEFAULT_FROM_EMAIL = 'FragDenStaat.de <info@fragdenstaat.de>'
    EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
    CELERY_EMAIL_BACKEND = 'froide.foirequest.smtp.EmailBackend'
    # EMAIL_HOST
    # EMAIL_HOST_PASSWORD
    # EMAIL_HOST_USER
    EMAIL_SUBJECT_PREFIX = '[AdminFragDenStaat] '
    EMAIL_USE_TLS = True
    EMAIL_PORT = 25
    # FOI_EMAIL_ACCOUNT_NAME
    # FOI_EMAIL_ACCOUNT_PASSWORD
    FOI_EMAIL_DOMAIN = ['fragdenstaat.de', 'echtemail.de']
    FOI_EMAIL_FIXED_FROM_ADDRESS = False
    FOI_EMAIL_FUNC = None
    # Values from env
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

    BOUNCE_EMAIL_PORT_IMAP = 143

    GEOIP_PATH = env('DJANGO_GEOIP_PATH')

    ELASTICSEARCH_INDEX_PREFIX = 'fragdenstaat_de'
    ELASTICSEARCH_DSL = {
        'default': {
            'hosts': 'localhost:9200'
        },
    }
    ELASTICSEARCH_DSL_SIGNAL_PROCESSOR = 'froide.helper.search.CelerySignalProcessor'

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
    MEDIA_URL = 'https://media.frag-den-staat.de/files/'

    FOI_MEDIA_TOKENS = True
    FOI_MEDIA_DOMAIN = 'https://media.frag-den-staat.de'

    FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o2750
    FILE_UPLOAD_PERMISSIONS = 0o640

    SECRET_KEY = env('DJANGO_SECRET_KEY')
    SECRET_URLS = {
        'admin': env('DJANGO_SECRET_URL_ADMIN')
    }

    _base_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '..')
    )
    RAVEN_CONFIG = {
        'release': raven.fetch_git_sha(_base_dir)
    }
    if env('DJANGO_SENTRY_DSN') is not None:
        RAVEN_CONFIG['dsn'] = env('DJANGO_SENTRY_DSN')
    RAVEN_JS_URL = env('DJANGO_SENTRY_PUBLIC_DSN')

    SERVER_EMAIL = 'info@fragdenstaat.de'

    SITE_EMAIL = 'info@fragdenstaat.de'
    SITE_ID = 1
    SITE_NAME = 'FragDenStaat'
    SITE_URL = 'https://fragdenstaat.de'
    META_SITE_PROTOCOL = 'https'

    TASTYPIE_DEFAULT_FORMATS = ['json']

    @property
    def OAUTH2_PROVIDER(self):
        P = super(FragDenStaat, self).OAUTH2_PROVIDER
        P['ALLOWED_REDIRECT_URI_SCHEMES'] = ['https', 'fragdenstaat']
        return P
