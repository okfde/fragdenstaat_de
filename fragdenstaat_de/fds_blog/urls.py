from django.urls import path, re_path
from django.utils.translation import gettext_lazy as _

from froide.api import api_router

from .api_views import ArticleTagViewSet
from .feeds import LatestArticlesFeed, LatestArticlesTeaserFeed
from .views import (
    ArticleArchiveView,
    ArticleDetailView,
    ArticleListView,
    ArticleSearchView,
    AuthorArticleView,
    CategoryArticleView,
    TaggedListView,
)

PERMALINKS_URLS = {
    "full_date": r"^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>\w[-\w]*)/$",
    "short_date": r"^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<slug>\w[-\w]*)/$",
    "category": r"^(?P<category>\w[-\w]*)/(?P<slug>\w[-\w]*)/$",
    "slug": r"^(?P<slug>\w[-\w]*)/$",
}


def get_urls():
    urls = PERMALINKS_URLS
    details = []
    for urlconf in urls.values():
        details.append(
            re_path(urlconf, ArticleDetailView.as_view(), name="article-detail"),
        )
    return details


app_name = "blog"
detail_urls = get_urls()

urlpatterns = [
    path("", ArticleListView.as_view(), name="article-latest"),
    re_path(_(r"^search/$"), ArticleSearchView.as_view(), name="article-search"),
    re_path(r"^feed/$", LatestArticlesFeed(), name="article-latest-feed"),
    re_path(
        r"^feed/teaser/$", LatestArticlesTeaserFeed(), name="article-latest-feed-teaser"
    ),
    re_path(
        r"^(?P<year>\d{4})/$", ArticleArchiveView.as_view(), name="article-archive"
    ),
    re_path(
        r"^(?P<year>\d{4})/(?P<month>\d{1,2})/$",
        ArticleArchiveView.as_view(),
        name="article-archive",
    ),
    re_path(
        _(r"^author/(?P<username>[\w\.@+-]+)/$"),
        AuthorArticleView.as_view(),
        name="article-author",
    ),
    re_path(
        _(r"^category/(?P<category>[\w\.@+-]+)/$"),
        CategoryArticleView.as_view(),
        name="article-category",
    ),
    re_path(r"^tag/(?P<tag>[-\w]+)/$", TaggedListView.as_view(), name="article-tagged"),
] + detail_urls

api_router.register(r"articletag", ArticleTagViewSet, basename="articletag")
