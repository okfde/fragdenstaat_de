from django.conf import settings


def theme_settings(request):
    return {
        "RAVEN_JS_URL": settings.SENTRY_JS_URL,
        "SENTRY_JS_URL": settings.SENTRY_JS_URL,
    }
