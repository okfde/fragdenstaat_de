from django.conf import settings


def page_site_settings(request, key, default=None):
    current_page = getattr(request, "current_page", None)
    if current_page and current_page.site_id != settings.SITE_ID:
        return current_page.site.site_settings.settings.get(key, default)
    return default


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
        # When rendering on main site
        "MAINSITE_BASE_TEMPLATE": page_site_settings(
            request, "CMSSITE_BASE_TEMPLATE", "cms/base.html"
        ),
    }


def site_settings(request):
    site_settings = request.site.site_settings.settings
    return site_settings
