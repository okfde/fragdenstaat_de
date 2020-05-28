from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib.sitemaps import views as sitemaps_views
from django.views.generic import TemplateView

# Import early to register with api_router
from froide_campaign import urls as campaign_urls
import fragdenstaat_de.fds_blog.urls  # noqa

from froide.foirequest.views import dashboard
from froide.urls import (
    froide_urlpatterns,
    admin_urls,
    jurisdiction_urls, sitemaps
)

from fragdenstaat_de.fds_cms.sitemaps import FdsCMSSitemap
from fragdenstaat_de.fds_blog.sitemaps import BlogSitemap, NewsSitemap

from .views import glyphosat_download, meisterschaften_tippspiel


sitemaps['cmspages'] = FdsCMSSitemap
sitemaps['blog'] = BlogSitemap

PROTOCOL = settings.SITE_URL.split(':')[0]

for klass in sitemaps.values():
    klass.protocol = PROTOCOL


sitemap_urlpatterns = [
    url(r'^sitemap\.xml$', sitemaps_views.index,
        {'sitemaps': sitemaps, 'sitemap_url_name': 'sitemaps'}),
    url(r'^sitemap-news.xml$', sitemaps_views.sitemap, {
        'sitemaps': {'news': NewsSitemap},
        'template_name': 'fds_blog/sitemaps/sitemap_news.xml'
        }, name='sitemap-news'),
    url(r'^sitemap-(?P<section>.+)\.xml$', sitemaps_views.sitemap,
        {'sitemaps': sitemaps}, name='sitemaps')
]

urlpatterns = [
    # url(r'^$', index, name='index'),
    url(r'^kampagne/', include(campaign_urls)),
    url(r'^temp/', TemplateView.as_view(template_name="snippets/temp.html")),
    url(r'^klagen/', include('froide_legalaction.urls')),
    url(r'^payments/', include('froide_payment.payments_urls')),
    url(r'^payment/', include('froide_payment.urls')),
    url(r'^dashboard/$', dashboard, name='dashboard'),
    url(r'^taggit_autosuggest/', include('taggit_autosuggest.urls')),
    url(r'^contractor/', include('contractor.urls')),
    url(r'^fax/', include('froide_fax.urls')),
    url(r'^newsletter/', include('fragdenstaat_de.fds_newsletter.urls')),
    url(r"^glyphosat-bfr/(?P<slug>[-\w]+)/(?P<message_id>\d+)/download-document/$", glyphosat_download, name="fragdenstaat-glyphosat_download"),
    url(r"^tippspiel/$", meisterschaften_tippspiel, name="fragdenstaat-meisterschaften_tippspiel"),
]

urlpatterns += [
    url(r'^', include('filer.server.urls')),
]

urlpatterns += sitemap_urlpatterns


if settings.DEBUG:
    from django.contrib.sites.models import Site  # noqa
    try:
        if not Site.objects.filter(id=settings.SITE_ID).exists():
            Site.objects.create(id=settings.SITE_ID,
                domain='localhost:8000', name='localhost')
    except Exception:
        # Possibly during migration, ignore
        pass


urlpatterns += i18n_patterns(
    *froide_urlpatterns,
    *jurisdiction_urls,
    *admin_urls,
    url(r'^', include('cms.urls')),
    prefix_default_language=False
)
