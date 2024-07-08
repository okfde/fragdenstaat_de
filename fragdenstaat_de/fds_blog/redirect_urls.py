from django.shortcuts import redirect
from django.urls import path, re_path
from django.utils.translation import gettext_lazy as _

from .redirect_views import (
    ArchiveRedirectView,
    AuthorRedirectView,
    CategoryRedirectView,
    SearchRedirectView,
    TagRedirectView,
)
from .views import ArticleRedirectView


def fixed_redirect(pattern_name):
    return lambda request: redirect(pattern_name, permanent=True)


ARTICLE_URLS = [
    r"^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>\w[-\w]*)/$",
    r"^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<slug>\w[-\w]*)/$",
    r"^(?P<category>\w[-\w]*)/(?P<slug>\w[-\w]*)/$",
    r"^(?P<slug>\w[-\w]*)/$",
]

urlpatterns = [
    path("", fixed_redirect("blog:article-latest"), name="legacy-article-latest"),
    re_path(
        _(r"^search/$"),
        SearchRedirectView.as_view(),
        name="legacy-article-search",
    ),
    re_path(
        r"^feed/$",
        fixed_redirect("blog:article-latest-feed"),
        name="legacy-article-latest-feed",
    ),
    re_path(
        r"^feed/audio/$",
        fixed_redirect("blog:article-latest-feed-audio"),
        name="legacy-article-latest-feed-audio",
    ),
    re_path(
        r"^feed/teaser/$",
        fixed_redirect("blog:article-latest-feed-teaser"),
        name="legacy-article-latest-feed-teaser",
    ),
    re_path(
        r"^(?P<year>\d{4})/$",
        ArchiveRedirectView.as_view(),
        name="legacy-article-archive",
    ),
    re_path(
        r"^(?P<year>\d{4})/(?P<month>\d{1,2})/$",
        ArchiveRedirectView.as_view(),
        name="legacy-article-archive",
    ),
    re_path(
        _(r"^author/(?P<username>[\w\.@+-]+)/$"),
        AuthorRedirectView.as_view(),
        name="legacy-article-author",
    ),
    re_path(
        _(r"^category/(?P<slug>[\w\.@+-]+)/$"),
        CategoryRedirectView.as_view(),
        name="legacy-article-category",
    ),
    re_path(
        r"^tag/(?P<tag>[-\w]+)/$",
        TagRedirectView.as_view(),
        name="legacy-article-tagged",
    ),
] + [
    re_path(urlconf, ArticleRedirectView.as_view(), name="legacy-article-redirect")
    for urlconf in ARTICLE_URLS
]
