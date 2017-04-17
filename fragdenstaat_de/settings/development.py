from .base import FragDenStaatBase


class Dev(FragDenStaatBase):
    pass


try:
    from .local_settings import *  # noqa
except ImportError:
    pass
