from django.core.exceptions import ValidationError


def validate_site_settings(value):
    default_keys = set(DEFAULT_SITE_SETTINGS.keys())
    if len(default_keys - set(value.keys())) > 0:
        raise ValidationError("Not all required site settings are given")


DEFAULT_SITE_SETTINGS = {
    "SITE_NAME": "",
    "SITE_EMAIL": "",
    "SITE_URL": "",
    "SITE_LOGO": "",
    "SENTRY_JS_URL": "",
    "MATOMO_SITE_ID": "",
    "CMSSITE_BASE_TEMPLATE": "cms/base.html",
}


def get_default_site_settings():
    return DEFAULT_SITE_SETTINGS.copy()
