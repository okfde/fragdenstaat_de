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
    "<int:pk>/",
]

redirect_urls = [
    path(urlconf, ArticleRedirectView.as_view()) for urlconf in REDIRECT_PATTERNS
]

# redirect urls need to come before actual urls: with /1970/01/01/foo/,
# "1970" could also be a category slug.

urlpatterns = (
    [path("", ArticleListView.as_view(), name="article-latest")]
    + redirect_urls
    + [
        path(
            "<slug:category>/<int:year>/<int:month>/<slug:slug>/",
            ArticleDetailView.as_view(),
            name="article-detail",
        ),
        path(_("search/"), ArticleSearchView.as_view(), name="article-search"),
        path("feed/", LatestArticlesFeed(), name="article-latest-feed"),
        path("feed/audio/", LatestAudioFeed(), name="article-latest-feed-audio"),
        path(
            "feed/teaser/",
            LatestArticlesTeaserFeed(),
            name="article-latest-feed-teaser",
        ),
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
        path(
            "<slug:category>/",
            root_slug_view,
            name="article-category",
        ),
        path("tag/<slug:tag>/", TaggedListView.as_view(), name="article-tagged"),
    ]
)

api_router.register(r"articletag", ArticleTagViewSet, basename="articletag")
