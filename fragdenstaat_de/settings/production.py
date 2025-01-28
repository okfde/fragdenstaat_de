import logging
import os

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from .base import FragDenStaatBase, env


class FragDenStaat(FragDenStaatBase):
    DEBUG = False
    TEMPLATE_DEBUG = False
    CELERY_TASK_ALWAYS_EAGER = False
    CELERY_TASK_EAGER_PROPAGATES = False
    CELERY_SEND_TASK_ERROR_EMAILS = True

    ADMINS = (("FragDenStaat.de", "mail@fragdenstaat.de"),)
    MANAGERS = (("FragDenStaat.de", "mail@fragdenstaat.de"),)

    SECURE_FRAME_DENY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True

    CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE", "1") == "1"
    CSRF_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE", "1") == "1"
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
    LANGUAGE_COOKIE_SECURE = env("LANGUAGE_COOKIE_SECURE", "1") == "1"
    LANGUAGE_COOKIE_SAMESITE = "Lax"

    DATA_UPLOAD_MAX_MEMORY_SIZE = 15728640  # 15 MB
    DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "overwrite": {
            # Replace in Django 5.1 with allow_overwrite Option
            "BACKEND": "froide.helper.storage.OverwriteStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
        },
    }

    STATIC_URL = env("STATIC_URL", "https://static.frag-den-staat.de/static/")
    CONTRACTOR_URL = STATIC_URL.replace("/static/", "/assets/")

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTOCOL", "https")

    INTERNAL_MEDIA_PREFIX = "/protected/"

    ALLOWED_HOSTS = [x for x in env("ALLOWED_HOSTS", "").split(",") if x]
    ALLOWED_HOSTS = ALLOWED_HOSTS + [
        "fragdenstaat.de",
        "media.frag-den-staat.de",
        "testserver",
    ]
    ALLOWED_REDIRECT_HOSTS = ALLOWED_HOSTS + ["sanktionsfrei.de"]
    CSRF_TRUSTED_ORIGINS = [x for x in env("CSRF_TRUSTED_ORIGINS", "").split(",") if x]

    PAYMENT_HOST = "fragdenstaat.de"
    PAYMENT_USES_SSL = True
    PAYMENT_VARIANTS = {
        "creditcard": (
            "froide_payment.provider.StripeIntentProvider",
            {
                "public_key": env("STRIPE_PUBLIC_KEY"),
                "secret_key": env("STRIPE_PRIVATE_KEY"),
                "signing_secret": env("STRIPE_WEBHOOK_CC_SIGNING_KEY"),
            },
        ),
        "sepa": (
            "froide_payment.provider.StripeSEPAProvider",
            {
                "public_key": env("STRIPE_PUBLIC_KEY"),
                "secret_key": env("STRIPE_PRIVATE_KEY"),
                "signing_secret": env("STRIPE_WEBHOOK_SEPA_SIGNING_KEY"),
            },
        ),
        "paypal": (
            "froide_payment.provider.PaypalProvider",
            {
                "client_id": env("PAYPAL_CLIENT_ID"),
                "secret": env("PAYPAL_CLIENT_SECRET"),
                "endpoint": env("PAYPAL_API_URL"),
                "capture": True,
                "webhook_id": env("PAYPAL_WEBHOOK_ID"),
            },
        ),
        "sofort": (
            "froide_payment.provider.StripeSofortProvider",
            {
                # Test API keys
                "public_key": env("STRIPE_PUBLIC_KEY"),
                "secret_key": env("STRIPE_PRIVATE_KEY"),
                # separate Webhook signing secret
                "signing_secret": env("STRIPE_WEBHOOK_SOFORT_SIGNING_KEY"),
            },
        ),
        "lastschrift": ("froide_payment.provider.LastschriftProvider", {}),
        "banktransfer": ("froide_payment.provider.BanktransferProvider", {}),
    }

    CACHE_KEY_PREFIX = env("CACHE_KEY_PREFIX", "fragdenstaat")
    CACHE_LOCAL_MEMORY = int(env("CACHE_LOCAL_MEMORY", "0"))
    if CACHE_LOCAL_MEMORY:
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "KEY_PREFIX": CACHE_KEY_PREFIX,
                "TIMEOUT": "3600",
            }
        }
    else:
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
                "LOCATION": env("MEMCACHED_LOCATION", "127.0.0.1:11211"),
                "KEY_PREFIX": CACHE_KEY_PREFIX,
                "TIMEOUT": "3600",
                "OPTIONS": {
                    "no_delay": True,
                    "ignore_exc": True,
                    "default_noreply": True,
                    "max_pool_size": 4,
                    "use_pooling": True,
                },
            }
        }

    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": env("DATABASE_NAME"),
            "OPTIONS": {},
            "HOST": env("DATABASE_HOST"),
            "USER": env("DATABASE_USER"),
            "PASSWORD": env("DATABASE_PASSWORD"),
            "CONN_MAX_AGE": 0,
            "PORT": "",
        }
    }

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("localhost", 6379)],
            },
        },
    }
    REDIS_URL = "redis://localhost"

    @property
    def TEMPLATES(self):
        TEMP = super(FragDenStaat, self).TEMPLATES
        TEMP[0]["OPTIONS"]["debug"] = False
        loaders = TEMP[0]["OPTIONS"]["loaders"]
        TEMP[0]["OPTIONS"]["loaders"] = [
            ("django.template.loaders.cached.Loader", loaders)
        ]
        return TEMP

    CELERY_BROKER_URL = env("DJANGO_CELERY_BROKER_URL")

    CUSTOM_AUTH_USER_MODEL_DB = "auth_user"

    DEFAULT_FROM_EMAIL = env(
        "DEFAULT_FROM_EMAIL", "FragDenStaat.de <info@fragdenstaat.de>"
    )
    EMAIL_BACKEND = "fragdenstaat_de.theme.email_backend.CustomCeleryEmailBackend"
    CELERY_EMAIL_BACKEND = "froide.foirequest.smtp.EmailBackend"
    # EMAIL_HOST
    # EMAIL_HOST_PASSWORD
    # EMAIL_HOST_USER
    EMAIL_SUBJECT_PREFIX = "[AdminFragDenStaat] "
    EMAIL_USE_TLS = True
    EMAIL_PORT = 25
    # FOI_EMAIL_ACCOUNT_NAME
    # FOI_EMAIL_ACCOUNT_PASSWORD
    FOI_EMAIL_DOMAIN = [
        x.strip()
        for x in env("FOI_MAIL_DOMAIN", "fragdenstaat.de,echtemail.de").split(",")
    ]
    FOI_MAIL_SERVER_HOST = env("FOI_MAIL_SERVER_HOST", "mail.fragdenstaat.de")
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
    FOI_MEDIA_PATH = "foi"

    BOUNCE_EMAIL_PORT_IMAP = 143

    GEOIP_PATH = env("DJANGO_GEOIP_PATH")

    ELASTICSEARCH_INDEX_PREFIX = "fragdenstaat_de"
    ELASTICSEARCH_DSL = {
        "default": {
            "hosts": env("DJANGO_ELASTICSEARCH_HOSTS", "http://localhost:9200").split(
                ","
            )
        },
    }
    ELASTICSEARCH_DSL_SIGNAL_PROCESSOR = "froide.helper.search.CelerySignalProcessor"

    LOGGING = {
        "loggers": {
            "": {"handlers": ["console"], "level": "WARNING"},
            "froide": {"level": "INFO", "propagate": True, "handlers": ["console"]},
            "fragdenstaat_de": {
                "level": "INFO",
                "propagate": True,
                "handlers": ["console"],
            },
            "froide_payment": {
                "level": "INFO",
                "propagate": True,
                "handlers": ["console"],
            },
            "sentry.errors": {
                "handlers": ["console"],
                "propagate": False,
                "level": "DEBUG",
            },
            "django.request": {
                "level": "ERROR",
                "propagate": True,
                "handlers": ["console"],
            },
        },
        "disable_existing_loggers": True,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "formatters": {
            "verbose": {
                "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
            }
        },
        "version": 1,
        "filters": {
            "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
            "ignore_501": {"()": "fragdenstaat_de.theme.utils.Ignore501Errors"},
        },
        "root": {"handlers": ["console"], "level": "WARNING"},
    }
    MANAGERS = (("FragDenStaat.de", "mail@fragdenstaat.de"),)
    MEDIA_ROOT = env("DJANGO_MEDIA_ROOT")
    MEDIA_URL = env("MEDIA_URL", "https://media.frag-den-staat.de/files/")

    FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o2750
    FILE_UPLOAD_PERMISSIONS = 0o640

    SECRET_KEY = env("DJANGO_SECRET_KEY")
    SECRET_URLS = {"admin": env("DJANGO_SECRET_URL_ADMIN")}

    THUMBNAIL_OPTIMIZE_COMMAND = {
        "png": "/usr/bin/optipng {filename}",
        "gif": "/usr/bin/optipng {filename}",
        "jpeg": "/usr/bin/jpegoptim {filename}",
    }
    FDS_THUMBNAIL_ENABLE_AVIF = True
    FILINGCABINET_ENABLE_WEBP = True

    _base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    SENTRY_JS_URL = env("DJANGO_SENTRY_PUBLIC_DSN")

    SERVER_EMAIL = env("SERVER_EMAIL", "info@fragdenstaat.de")

    SITE_EMAIL = env("SITE_EMAIL", "info@fragdenstaat.de")
    SITE_ID = 1
    SITE_NAME = "FragDenStaat"
    SITE_URL = env("SITE_URL", "https://fragdenstaat.de") or "https://fragdenstaat.de"
    META_SITE_PROTOCOL = "https"

    TASTYPIE_DEFAULT_FORMATS = ["json"]


class FragDenStaatDebug(FragDenStaat):
    LOGGING = dict(FragDenStaat.LOGGING)
    LOGGING["disable_existing_loggers"] = False
    LOGGING["loggers"][""] = {"handlers": ["console"], "level": "DEBUG"}


sentry_logging = LoggingIntegration(
    level=logging.INFO,  # Capture info and above as breadcrumbs
    event_level=logging.ERROR,  # Send errors as events
)
sentry_sdk.init(
    dsn=env("DJANGO_SENTRY_DSN"),
    release=env("RELEASE_VERSION"),
    integrations=[sentry_logging, DjangoIntegration(), CeleryIntegration()],
    traces_sample_rate=0.2,
)
