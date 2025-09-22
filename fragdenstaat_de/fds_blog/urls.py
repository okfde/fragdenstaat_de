from django.urls import path
from django.utils.translation import gettext_lazy as _

from .feeds import LatestArticlesFeed, LatestArticlesTeaserFeed, LatestAudioFeed
from .views import (
    ArticleArchiveView,
    ArticleDetailView,
    ArticleListView,
    ArticleSearchView,
    AuthorArticleView,
    TaggedListView,
    root_slug_view,
)

app_name = "blog"

# the order is important!
# /1970/01/ could be /<slug:category>/<slug:slug>/ (article page),
# but archive at /<int:year>/<int:month>/ (with stricter url params) should have higher priority
urlpatterns = [
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
    path("tag/<str:tags>/", TaggedListView.as_view(), name="article-tagged"),
    path(_("search/"), ArticleSearchView.as_view(), name="article-search"),
    path("feed/", LatestArticlesFeed(), name="article-latest-feed"),
    path("feed/audio/", LatestAudioFeed(), name="article-latest-feed-audio"),
    path(
        "feed/teaser/",
        LatestArticlesTeaserFeed(),
        name="article-latest-feed-teaser",
    ),
] + [
    path(
        "<slug:category>/<int:year>/<int:month>/<slug:slug>/",
        ArticleDetailView.as_view(),
        name="article-detail",
    ),
    path(
        "<slug:slug>/",
        root_slug_view,
        name="article-category",
    ),
]
