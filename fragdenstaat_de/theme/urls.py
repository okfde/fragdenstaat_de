from django.conf import settings
from django.conf.urls import include, url
from django.contrib.flatpages import views
from django.contrib.sitemaps import views as sitemaps_views

from froide.urls import (
    froide_urlpatterns, help_urlpatterns,
    jurisdiction_urls, sitemaps
)

from cms.sitemaps import CMSSitemap
from djangocms_blog.sitemaps import BlogSitemap

from .views import index, gesetze_dashboard


sitemaps['cmspages'] = CMSSitemap
sitemaps['blog'] = BlogSitemap

PROTOCOL = settings.SITE_URL.split(':')[0]

for klass in sitemaps.values():
    klass.protocol = PROTOCOL


sitemap_urlpatterns = [
    url(r'^sitemap\.xml$', sitemaps_views.index,
        {'sitemaps': sitemaps, 'sitemap_url_name': 'sitemaps'}),
    url(r'^sitemap-(?P<section>.+)\.xml$', sitemaps_views.sitemap,
        {'sitemaps': sitemaps}, name='sitemaps')
]

urlpatterns = [
    url(r'^hilfe/spenden/$', views.flatpage, {'url': '/hilfe/spenden/'}, name='help-donate'),
    url(r'^kampagne/', include('froide_campaign.urls')),
    url(r'^klagen/', include('froide_legalaction.urls')),
    url(r'^gesetze/dashboard/$', gesetze_dashboard, name='fragdenstaat-gesetze_dashboard'),
    url(r'^$', index, name='index'),
    url(r'^taggit_autosuggest/', include('taggit_autosuggest.urls')),
]

urlpatterns += [
    url(r'^', include('filer.server.urls')),
]

urlpatterns += (
    sitemap_urlpatterns +
    froide_urlpatterns +
    help_urlpatterns +
    jurisdiction_urls
)

urlpatterns += [
    url(r'^', include('cms.urls')),
]
