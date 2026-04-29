from django.conf import settings


def theme_settings(request):
    return {
        "SENTRY_JS_URL": settings.SENTRY_JS_URL,
        "MATOMO_SITE_ID": settings.MATOMO_SITE_ID,
        "EASYLANG_ENABLED": getattr(settings, "EASYLANG_ENABLED", False),
    }
