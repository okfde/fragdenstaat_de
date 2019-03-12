from django.conf import settings


def theme_settings(request):
    return {
        'RAVEN_JS_URL': settings.RAVEN_JS_URL
    }
