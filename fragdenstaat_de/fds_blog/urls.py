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

REDIRECT_URLS = {
    "full_date": "<int:year>/<int:month>/<int:day>/<slug:slug>/",
    "category": "<slug:category>/<slug:slug>/",
}


def get_redirect_urls():
    urls = REDIRECT_URLS
    details = []
    for urlconf in urls.values():
        details.append(
            path(
                urlconf, ArticleRedirectView.as_view(), name="article-detail-redirect"
            ),
        )
    return details


app_name = "blog"
redirect_urls = get_redirect_urls()

urlpatterns = [
    path("", ArticleListView.as_view(), name="article-latest"),
    path(
        _("<slug:category>/<int:year>/<int:month>/<slug:slug>/"),
        ArticleDetailView.as_view(),
        name="article-detail",
    ),
    path(
        _("<int:year>/<int:month>/<slug:slug>/"),
        ArticleDetailView.as_view(),
        name="article-detail",
    ),
    path(_("search/"), ArticleSearchView.as_view(), name="article-search"),
    path("feed/", LatestArticlesFeed(), name="article-latest-feed"),
    path("feed/audio/", LatestAudioFeed(), name="article-latest-feed-audio"),
    path("feed/teaser/", LatestArticlesTeaserFeed(), name="article-latest-feed-teaser"),
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
] + redirect_urls

api_router.register(r"articletag", ArticleTagViewSet, basename="articletag")
