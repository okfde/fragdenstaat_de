from django.conf.urls import url
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from djangocms_blog.feeds import LatestEntriesFeed, TagFeed
from djangocms_blog.views import (
    AuthorEntriesView, CategoryEntriesView, PostArchiveView, PostListView,
    TaggedListView,
)
from djangocms_blog.urls import get_urls

User = get_user_model()


class CustomAuthorEntriesView(AuthorEntriesView):
    view_url_name = 'djangocms_blog:posts-author'

    def get_queryset(self):
        qs = super(AuthorEntriesView, self).get_queryset()
        if 'username' in self.kwargs:
            qs = qs.filter(author__username=self.kwargs['username'])
        return self.optimize(qs)

    def get_context_data(self, **kwargs):
        kwargs['author'] = get_object_or_404(
            User, username=self.kwargs.get('username')
        )
        context = super(AuthorEntriesView, self).get_context_data(**kwargs)
        return context


class FeaturedPostListView(PostListView):
    def get_queryset(self):
        qs = super(FeaturedPostListView, self).get_queryset()

        self.featured = None
        page = self.request.GET.get('page', None)
        if not page or page == '1':
            try:
                self.featured = qs.filter(
                    date_featured__isnull=False).order_by('-date_featured')[0]
            except IndexError:
                pass

        if self.featured is not None:
            qs = qs.exclude(pk=self.featured.pk)
        return qs

    def get_context_data(self, **kwargs):
        context = super(FeaturedPostListView, self).get_context_data(**kwargs)
        context['featured'] = self.featured
        return context


detail_urls = get_urls()

urlpatterns = [
    url(r'^$',
        FeaturedPostListView.as_view(), name='posts-latest'),
    url(r'^feed/$',
        LatestEntriesFeed(), name='posts-latest-feed'),
    url(r'^(?P<year>\d{4})/$',
        PostArchiveView.as_view(), name='posts-archive'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        PostArchiveView.as_view(), name='posts-archive'),
    url(r'^autor/(?P<username>[\w\.@+-]+)/$',
        CustomAuthorEntriesView.as_view(), name='posts-author'),
    url(r'^kategorie/(?P<category>[\w\.@+-]+)/$',
        CategoryEntriesView.as_view(), name='posts-category'),
    url(r'^tag/(?P<tag>[-\w]+)/$',
        TaggedListView.as_view(), name='posts-tagged'),
    url(r'^tag/(?P<tag>[-\w]+)/feed/$',
        TagFeed(), name='posts-tagged-feed'),
] + detail_urls
