import os

from configurations import values

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

from .base import THEME_ROOT, FragDenStaatBase, env


class Test(FragDenStaatBase):
    @property
    def INSTALLED_APPS(self):
        return super().INSTALLED_APPS + ["django_extended_makemessages"]

    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    ALLOWED_HOSTS = ("localhost", "testserver")

    DEBUG = False

    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]

    MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

    TEST_SELENIUM_DRIVER = values.Value("chrome")
    ROOT_URLCONF = "tests.urls"

    GEOIP_PATH = None

    DATABASES = values.DatabaseURLValue(
        "postgis://fragdenstaat_de:fragdenstaat_de@127.0.0.1:5432/fragdenstaat_de"
    )
    ELASTICSEARCH_INDEX_PREFIX = "fds_test"
    ELASTICSEARCH_DSL = {
        "default": {"hosts": "http://localhost:9200"},
    }
    FIXTURE_DIRS = [os.path.join(THEME_ROOT, "..", "tests", "fixtures")]

    PAYMENT_VARIANTS = {
        # 'default': ('payments.dummy.DummyProvider', {})
        "creditcard": (
            "froide_payment.provider.StripeIntentProvider",
            {
                # Test API keys
                "public_key": env("STRIPE_TEST_PUBLIC_KEY"),
                "secret_key": env("STRIPE_TEST_SECRET_KEY"),
            },
        ),
        "sepa": (
            "froide_payment.provider.StripeSEPAProvider",
            {
                # Test API keys
                "public_key": env("STRIPE_TEST_PUBLIC_KEY"),
                "secret_key": env("STRIPE_TEST_SECRET_KEY"),
            },
        ),
        "paypal": (
            "froide_payment.provider.PaypalProvider",
            {
                "client_id": env("PAYPAL_TEST_CLIENT_ID"),
                "secret": env("PAYPAL_TEST_SECRET"),
                "endpoint": "https://api.sandbox.paypal.com",
                "capture": True,
                "webhook_id": None,
            },
        ),
        "lastschrift": ("froide_payment.provider.LastschriftProvider", {}),
        "banktransfer": ("froide_payment.provider.BanktransferProvider", {}),
    }
