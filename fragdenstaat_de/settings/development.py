from fragdenstaat_de.settings.cms import CMSSiteBase, GegenrechtsschutzMixin

from .base import FragDenStaatBase, env


class DevMixin:
    FRONTEND_DEBUG = True


class Dev(DevMixin, FragDenStaatBase):
    GEOIP_PATH = None

    CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": env("DATABASE_NAME", "fragdenstaat_de"),
            "OPTIONS": {},
            "HOST": "localhost",
            "USER": env("DATABASE_USER", "fragdenstaat_de"),
            "PASSWORD": env("DATABASE_PASSWORD", "fragdenstaat_de"),
            "PORT": "5432",
        }
    }

    @property
    def TEMPLATES(self):
        TEMP = super().TEMPLATES
        TEMP[0]["OPTIONS"]["debug"] = True
        return TEMP


class Gegenrechtsschutz(GegenrechtsschutzMixin, DevMixin, CMSSiteBase):
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": env("DATABASE_NAME", "fragdenstaat_de"),
            "OPTIONS": {},
            "HOST": "localhost",
            "USER": env("DATABASE_USER", "fragdenstaat_de_readonly"),
            "PASSWORD": env("DATABASE_PASSWORD", "fragdenstaat_de"),
            "PORT": "5432",
        }
    }


try:
    from .local_settings import Dev  # noqa
except ImportError:
    pass


try:
    from .local_settings import Gegenrechtsschutz  # noqa
except ImportError:
    pass
