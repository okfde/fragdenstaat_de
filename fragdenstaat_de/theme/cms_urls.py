from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps import views as sitemaps_views
from django.urls import include, path

from froide.account.views import bad_login_view_redirect

from fragdenstaat_de.fds_cms.sitemaps import FdsCMSSitemap

sitemaps = {"cmspages": FdsCMSSitemap}

PROTOCOL = settings.SITE_URL.split(":")[0]

for klass in sitemaps.values():
    klass.protocol = PROTOCOL


sitemap_urlpatterns = [
    path(
        "sitemap.xml",
        sitemaps_views.index,
        {"sitemaps": sitemaps, "sitemap_url_name": "sitemaps"},
    ),
    path(
        "sitemap-<slug:section>.xml",
        sitemaps_views.sitemap,
        {"sitemaps": sitemaps},
        name="sitemaps",
    ),
]

urlpatterns = [
    path("", include("filer.server.urls")),
]

urlpatterns += sitemap_urlpatterns


SECRET_URLS = getattr(settings, "SECRET_URLS", {})
urlpatterns += i18n_patterns(
    path("%s/login/" % SECRET_URLS.get("admin", "admin"), bad_login_view_redirect),
    path("%s/" % SECRET_URLS.get("admin", "admin"), admin.site.urls),
    path("", include("cms.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
