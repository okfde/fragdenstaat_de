from django.conf import settings
from django.urls import include, path
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import pgettext_lazy
from django.contrib.sitemaps import views as sitemaps_views

# Import early to register with api_router
from froide_campaign import urls as campaign_urls
import fragdenstaat_de.fds_blog.urls  # noqa

from froide.foirequest.views import dashboard
from froide.urls import (
    froide_urlpatterns,
    api_urlpatterns,
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
    path('sitemap.xml', sitemaps_views.index,
        {'sitemaps': sitemaps, 'sitemap_url_name': 'sitemaps'}),
    path('sitemap-news.xml', sitemaps_views.sitemap, {
        'sitemaps': {'news': NewsSitemap},
        'template_name': 'fds_blog/sitemaps/sitemap_news.xml'
        }, name='sitemap-news'),
    path('sitemap-<slug:section>.xml', sitemaps_views.sitemap,
        {'sitemaps': sitemaps}, name='sitemaps')
]

urlpatterns = [
    # url(r'^$', index, name='index'),
    path('klagen/', include('froide_legalaction.urls')),
    path('payments/', include('froide_payment.payments_urls')),
    path('payment/', include('froide_payment.urls')),
    path('dashboard/', dashboard, name='dashboard'),
    path('taggit_autosuggest/', include('taggit_autosuggest.urls')),
    path('contractor/', include('contractor.urls')),
    path('fax/', include('froide_fax.urls')),
    path('newsletter/update/', include('fragdenstaat_de.fds_newsletter.urls')),
    path('newsletter/archive/', include('fragdenstaat_de.fds_mailing.urls')),
    path("glyphosat-bfr/<slug:slug>/<int:message_id>/download-document/", glyphosat_download, name="fragdenstaat-glyphosat_download"),
    path("tippspiel/", meisterschaften_tippspiel, name="fragdenstaat-meisterschaften_tippspiel"),
    path("", include('fragdenstaat_de.fds_ogimage.urls'))
]

urlpatterns += [
    path('', include('filer.server.urls')),
]

urlpatterns += api_urlpatterns
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
    path(pgettext_lazy('url part', 'campaign/'), include(campaign_urls)),
    path('', include('cms.urls')),
    prefix_default_language=False
)
