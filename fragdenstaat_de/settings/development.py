from .base import FragDenStaatBase, env


class Dev(FragDenStaatBase):
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


try:
    from .local_settings import Dev  # noqa
except ImportError:
    pass
