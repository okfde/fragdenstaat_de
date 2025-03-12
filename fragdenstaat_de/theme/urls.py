from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib.sitemaps import views as sitemaps_views
from django.urls import include, path
from django.utils.translation import pgettext_lazy

from fcdocs_annotate.annotation.api import FeatureViewSet
from froide_campaign import urls as campaign_urls
from froide_govplan.admin import govplan_admin_site

from froide.urls import (
    admin_urls,
    api_urlpatterns,
    froide_urlpatterns,
    jurisdiction_urls,
    sitemaps,
)

from fragdenstaat_de.fds_blog.sitemaps import BlogSitemap, NewsSitemap
from fragdenstaat_de.fds_cms.sitemaps import FdsCMSSitemap
from fragdenstaat_de.fds_cms.views import scannerapp_postupload
from fragdenstaat_de.fds_newsletter.views import legacy_unsubscribe

from .views import (
    FDSAnnotationView,
    glyphosat_download,
    meisterschaften_tippspiel,
)

sitemaps["cmspages"] = FdsCMSSitemap
sitemaps["blog"] = BlogSitemap

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
        "sitemap-news.xml",
        sitemaps_views.sitemap,
        {
            "sitemaps": {"news": NewsSitemap},
            "template_name": "fds_blog/sitemaps/sitemap_news.xml",
        },
        name="sitemap-news",
    ),
    path(
        "sitemap-<slug:section>.xml",
        sitemaps_views.sitemap,
        {"sitemaps": sitemaps},
        name="sitemaps",
    ),
]

urlpatterns = [
    # url(r'^$', index, name='index'),
    path("klagen/", include("froide_legalaction.urls")),
    path("payments/", include("froide_payment.payments_urls")),
    path("payment/", include("froide_payment.urls")),
    path("contractor/", include("contractor.urls")),
    path("fax/", include("froide_fax.urls")),
    path("paperless/", include("fragdenstaat_de.fds_paperless.urls")),
    path("newsletter/update/", include("fragdenstaat_de.fds_newsletter.urls")),
    path("newsletter/archive/", include("fragdenstaat_de.fds_mailing.urls")),
    path(
        "newsletter/<slug:newsletter_slug>/subscription/<str:email>/unsubscribe/activate/<slug:activation_code>/",
        legacy_unsubscribe,
        name="newsletter_confirm_unsubscribe_legacy",
    ),
    path(
        "glyphosat-bfr/<slug:slug>/<int:message_id>/download-document/",
        glyphosat_download,
        name="fragdenstaat-glyphosat_download",
    ),
    path("fronteximport/", include("fragdenstaat_de.fds_fximport.urls")),
    path("koalitionstracker/admin/", govplan_admin_site.urls),
    path(
        "tippspiel/",
        meisterschaften_tippspiel,
        name="fragdenstaat-meisterschaften_tippspiel",
    ),
    path(
        "app/scanner/postupload/<slug:message_type>/<int:message_pk>/",
        scannerapp_postupload,
        name="fragdenstaat-scannerapp_postupload",
    ),
    path("fcdocs_annotate/", FDSAnnotationView.as_view(), name="annotate-view"),
    path(
        "api/v1/feature/", FeatureViewSet.as_view({"get": "list"}), name="api-features"
    ),
    path(
        "api/v1/feature/<int:pk>/",
        FeatureViewSet.as_view({"get": "retrieve"}),
        name="api-features-detail",
    ),
]

urlpatterns += [
    path("", include("filer.server.urls")),
]

urlpatterns += api_urlpatterns
urlpatterns += sitemap_urlpatterns


if settings.DEBUG:
    from django.contrib.sites.models import Site  # noqa

    try:
        if not Site.objects.filter(id=settings.SITE_ID).exists():
            Site.objects.create(
                id=settings.SITE_ID, domain="localhost:8000", name="localhost"
            )
    except Exception:
        # Possibly during migration, ignore
        pass


urlpatterns += i18n_patterns(
    *froide_urlpatterns,
    *jurisdiction_urls,
    *admin_urls,
    path("", include("fragdenstaat_de.fds_blog.redirect_urls"), name="blog-redirects"),
    path("", include("fragdenstaat_de.fds_ogimage.urls")),
    path(pgettext_lazy("url part", "campaign/"), include(campaign_urls)),
    path("", include("cms.urls")),
    prefix_default_language=False,
)
