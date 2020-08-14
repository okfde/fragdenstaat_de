import os

from configurations import values

from .base import FragDenStaatBase, THEME_ROOT


class Test(FragDenStaatBase):
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    ALLOWED_HOSTS = ('localhost', 'testserver')

    DEBUG = False

    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]

    MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'
    CACHES = values.CacheURLValue('locmem://')

    TEST_SELENIUM_DRIVER = values.Value('chrome')
    ROOT_URLCONF = 'tests.urls'

    GEOIP_PATH = None

    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': 'fragdenstaat_de',
            'USER': 'fragdenstaat_de',
            'PASSWORD': 'fragdenstaat_de',
            'HOST': '',
            'PORT': '',
        }
    }
    ELASTICSEARCH_INDEX_PREFIX = 'fds_test'
    ELASTICSEARCH_DSL = {
        'default': {
            'hosts': 'localhost:9200'
        },
    }
    FIXTURE_DIRS = [os.path.join(THEME_ROOT, '..', 'tests', 'fixtures')]
