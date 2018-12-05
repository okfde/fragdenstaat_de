from django.conf import settings
from django.conf.urls import include, url
from django.contrib.sitemaps import views as sitemaps_views
from django.views.generic import TemplateView

# Import early to register with api_router
from froide_campaign import urls as campaign_urls

from froide.foirequest.views import dashboard
from froide.urls import (
    froide_urlpatterns,
    jurisdiction_urls, sitemaps
)

from cms.sitemaps import CMSSitemap
from djangocms_blog.sitemaps import BlogSitemap

from .sitemaps import NewsSitemap


sitemaps['cmspages'] = CMSSitemap
sitemaps['blog'] = BlogSitemap

PROTOCOL = settings.SITE_URL.split(':')[0]

for klass in sitemaps.values():
    klass.protocol = PROTOCOL


sitemap_urlpatterns = [
    url(r'^sitemap\.xml$', sitemaps_views.index,
        {'sitemaps': sitemaps, 'sitemap_url_name': 'sitemaps'}),
    url(r'^sitemap-news.xml$', sitemaps_views.sitemap, {
        'sitemaps': {'news': NewsSitemap},
        'template_name': 'sitemaps/sitemap_news.xml'
        }, name='sitemap-news'),
    url(r'^sitemap-(?P<section>.+)\.xml$', sitemaps_views.sitemap,
        {'sitemaps': sitemaps}, name='sitemaps')
]

urlpatterns = [
    # url(r'^$', index, name='index'),
    url(r'^kampagne/', include(campaign_urls)),
    url(r'^temp/', TemplateView.as_view(template_name="snippets/temp.html")),
    url(r'^klagen/', include('froide_legalaction.urls')),
    url(r'^dashboard/$', dashboard, name='dashboard'),
    url(r'^taggit_autosuggest/', include('taggit_autosuggest.urls')),
    url(r'^fax/', include('froide_fax.urls')),
    url(r'^newsletter/', include('fragdenstaat_de.fds_newsletter.urls')),
]

urlpatterns += [
    url(r'^', include('filer.server.urls')),
]

urlpatterns += (
    sitemap_urlpatterns +
    froide_urlpatterns +
    jurisdiction_urls
)


if settings.DEBUG:
    from django.contrib.sites.models import Site  # noqa
    try:
        if not Site.objects.filter(id=settings.SITE_ID).exists():
            Site.objects.create(id=settings.SITE_ID,
                domain='localhost:8000', name='localhost')
    except Exception as e:
        # Possibly during migration, ignore
        pass

urlpatterns += [
    url(r'^', include('cms.urls')),
]
