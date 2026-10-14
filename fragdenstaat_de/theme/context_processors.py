from django.conf import settings


def theme_settings(request):
    return {
        "SENTRY_JS_URL": settings.SENTRY_JS_URL,
        "MATOMO_SITE_ID": settings.MATOMO_SITE_ID,
        "EASYLANG_ENABLED": getattr(settings, "EASYLANG_ENABLED", False),
        "CURRENT_LANGUAGE_CODE": getattr(
            request, "LANGUAGE_CODE", settings.LANGUAGE_CODE
        ),
        "DEFAULT_LANGUAGE_CODE": settings.LANGUAGE_CODE,
        "USER_LANGUAGES": getattr(settings, "USER_LANGUAGES", settings.LANGUAGES),
    }


def site_settings(request):
    site_settings = request.site.site_settings.settings
    return site_settings
