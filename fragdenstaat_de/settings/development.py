from .base import FragDenStaatBase


class Dev(FragDenStaatBase):
    GEOIP_PATH = None
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
        }
    }


try:
    from .local_settings import Dev  # noqa
except ImportError as e:
    pass
