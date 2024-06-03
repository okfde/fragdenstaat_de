from django.urls import path
from django.utils.translation import gettext_lazy as _

from froide.api import api_router

from .api_views import ArticleTagViewSet
from .feeds import LatestArticlesFeed, LatestArticlesTeaserFeed, LatestAudioFeed
from .views import (
    ArticleArchiveView,
    ArticleDetailView,
    ArticleListView,
    ArticleRedirectView,
    ArticleSearchView,
    AuthorArticleView,
    CategoryArticleRedirectView,
    TaggedListView,
    root_slug_view,
)

app_name = "blog"

REDIRECT_PATTERNS = [
    "<int:year>/<int:month>/<int:day>/<slug:slug>/",
    "<int:year>/<int:month>/<slug:slug>/",
    "<slug:category>/<slug:slug>/",
]

redirect_urls = [
    path(urlconf, ArticleRedirectView.as_view()) for urlconf in REDIRECT_PATTERNS
]

# the order is important!
# /1970/01/ could be /<slug:category>/<slug:slug>/ (article page),
# but archive at /<int:year>/<int:month>/ (with stricter url params) should have higher priority
urlpatterns = (
    [
        path("", ArticleListView.as_view(), name="article-latest"),
        path("<int:year>/", ArticleArchiveView.as_view(), name="article-archive"),
        path(
            "<int:year>/<int:month>/",
            ArticleArchiveView.as_view(),
            name="article-archive",
        ),
        path(
            _("author/<str:username>/"),
            AuthorArticleView.as_view(),
            name="article-author",
        ),
        path(
            _("category/<slug:category>/"),
            CategoryArticleRedirectView.as_view(),
            name="article-category-redirect",
        ),
        path("tag/<slug:tag>/", TaggedListView.as_view(), name="article-tagged"),
        path(_("search/"), ArticleSearchView.as_view(), name="article-search"),
        path("feed/", LatestArticlesFeed(), name="article-latest-feed"),
        path("feed/audio/", LatestAudioFeed(), name="article-latest-feed-audio"),
        path(
            "feed/teaser/",
            LatestArticlesTeaserFeed(),
            name="article-latest-feed-teaser",
        ),
    ]
    + redirect_urls
    + [
        path(
            "<slug:category>/<int:year>/<int:month>/<slug:slug>/",
            ArticleDetailView.as_view(),
            name="article-detail",
        ),
        path(
            "<slug:category>/",
            root_slug_view,
            name="article-category",
        ),
    ]
)

SHORT_ARTICLE_URL = path("p/", ArticleRedirectView.as_view(), name="article-short-url")

api_router.register(r"articletag", ArticleTagViewSet, basename="articletag")
