from django.conf.urls import url

from .feeds import LatestArticlesFeed
from .views import (
    AuthorArticleView, CategoryArticleView, ArticleArchiveView, ArticleDetailView, ArticleListView,
    TaggedListView,
)


PERMALINKS_URLS = {
    'full_date': r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>\w[-\w]*)/$',
    'short_date': r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<slug>\w[-\w]*)/$',
    'category': r'^(?P<category>\w[-\w]*)/(?P<slug>\w[-\w]*)/$',
    'slug': r'^(?P<slug>\w[-\w]*)/$',
}


def get_urls():
    urls = PERMALINKS_URLS
    details = []
    for urlconf in urls.values():
        details.append(
            url(urlconf, ArticleDetailView.as_view(), name='article-detail'),
        )
    return details


detail_urls = get_urls()

urlpatterns = [
    url(r'^$',
        ArticleListView.as_view(), name='article-latest'),
    url(r'^feed/$',
        LatestArticlesFeed(),
        name='article-latest-feed'),
    url(r'^(?P<year>\d{4})/$',
        ArticleArchiveView.as_view(), name='article-archive'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        ArticleArchiveView.as_view(), name='article-archive'),
    url(r'^autor/(?P<username>[\w\.@+-]+)/$',
        AuthorArticleView.as_view(), name='article-author'),
    url(r'^kategorie/(?P<category>[\w\.@+-]+)/$',
        CategoryArticleView.as_view(), name='article-category'),
    url(r'^tag/(?P<tag>[-\w]+)/$',
        TaggedListView.as_view(), name='article-tagged'),
    # url(r'^tag/(?P<tag>[-\w]+)/feed/$',
    #     TagFeed(), name='article-tagged-feed'),
] + detail_urls
