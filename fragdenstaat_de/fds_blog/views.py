import os.path

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.utils.translation import get_language
from django.views.generic import DetailView, ListView

from .models import Category, Article

User = get_user_model()


class BaseBlogView(object):
    model = Article

    def optimize(self, qs):
        return qs.prefetch_related(
            'categories', 'authors'
        )

    def get_view_url(self):
        if not self.view_url_name:
            raise ImproperlyConfigured(
                'Missing `view_url_name` attribute on {0}'.format(self.__class__.__name__)
            )

        url = reverse(
            self.view_url_name,
            args=self.args,
            kwargs=self.kwargs,
            current_app=self.namespace
        )
        return self.request.build_absolute_uri(url)

    def get_queryset(self):
        if not getattr(self.request, 'toolbar', False) or not self.request.toolbar.edit_mode:
            queryset = self.model.published.all()
        else:
            queryset = self.model._default_manager.all()
        if self.request.LANGUAGE_CODE != settings.LANGUAGE_CODE:
            queryset = queryset.filter(language=self.request.LANGUAGE_CODE)
        return self.optimize(queryset)

    def get_template_names(self):
        template_path = 'fds_blog'
        return os.path.join(template_path, self.base_template_name)


class BaseBlogListView(BaseBlogView):
    context_object_name = 'article_list'
    base_template_name = 'article_list.html'

    def get_context_data(self, **kwargs):
        context = super(BaseBlogListView, self).get_context_data(**kwargs)
        return context

    def get_paginate_by(self, queryset):
        return 12


class ArticleDetailView(BaseBlogView, DetailView):
    base_template_name = 'article_detail.html'
    slug_field = 'slug'
    view_url_name = 'fds_blog:article-detail'

    def get(self, *args, **kwargs):
        if hasattr(self.request, 'toolbar'):
            self.request.toolbar.set_object(self.get_object())
        return super().get(*args, **kwargs)


class ArticleListView(BaseBlogListView, ListView):
    view_url_name = 'fds_blog:article-latest'

    def get_queryset(self):
        qs = super().get_queryset()

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
        context = super().get_context_data(**kwargs)
        context['featured'] = self.featured
        return context


class ArticleArchiveView(BaseBlogListView, ListView):
    date_field = 'start_publication'
    allow_empty = True
    allow_future = True
    view_url_name = 'fds_blog:article-archive'

    def get_queryset(self):
        qs = super().get_queryset()
        if 'month' in self.kwargs:
            qs = qs.filter(**{'%s__month' % self.date_field: self.kwargs['month']})
        if 'year' in self.kwargs:
            qs = qs.filter(**{'%s__year' % self.date_field: self.kwargs['year']})
        return self.optimize(qs)

    def get_context_data(self, **kwargs):
        kwargs['month'] = int(self.kwargs.get('month')) if 'month' in self.kwargs else None
        kwargs['year'] = int(self.kwargs.get('year')) if 'year' in self.kwargs else None
        if kwargs['year']:
            kwargs['archive_date'] = now().replace(kwargs['year'], kwargs['month'] or 1, 1)
        context = super().get_context_data(**kwargs)
        return context


class TaggedListView(BaseBlogListView, ListView):
    view_url_name = 'fds_blog:article-tagged'

    def get_queryset(self):
        qs = super().get_queryset()
        return self.optimize(qs.filter(tags__slug=self.kwargs['tag']))

    def get_context_data(self, **kwargs):
        kwargs['tagged_articles'] = (self.kwargs.get('tag')
                                    if 'tag' in self.kwargs else None)
        context = super().get_context_data(**kwargs)
        return context


class AuthorArticleView(BaseBlogListView, ListView):
    view_url_name = 'fds_blog:article-author'

    def get_queryset(self):
        qs = super().get_queryset()
        if 'username' in self.kwargs:
            qs = qs.filter(authors__user__username=self.kwargs['username'])
        return self.optimize(qs)

    def get_context_data(self, **kwargs):
        kwargs['author'] = get_object_or_404(
            User,
            username=self.kwargs.get('username')
        )
        context = super().get_context_data(**kwargs)
        return context


class CategoryArticleView(BaseBlogListView, ListView):
    _category = None
    view_url_name = 'fds_blog:article-category'

    @property
    def category(self):
        if not self._category:
            try:
                self._category = Category.objects.active_translations(
                    get_language(), slug=self.kwargs['category']
                ).get()
            except Category.DoesNotExist:
                raise Http404
        return self._category

    def get(self, *args, **kwargs):
        # submit object to cms toolbar to get correct language switcher behavior
        if hasattr(self.request, 'toolbar'):
            self.request.toolbar.set_object(self.category)
        return super().get(*args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        if 'category' in self.kwargs:
            qs = qs.filter(categories=self.category.pk)
        return self.optimize(qs)

    def get_context_data(self, **kwargs):
        kwargs['category'] = self.category
        context = super().get_context_data(**kwargs)
        return context
