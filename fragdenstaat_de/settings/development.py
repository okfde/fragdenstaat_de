from .base import FragDenStaatBase


class Dev(FragDenStaatBase):
    GEOIP_PATH = None
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
        }
    }
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
        }
    }


try:
    from .local_settings import Dev  # noqa
except ImportError as e:
    pass
