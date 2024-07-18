from __future__ import annotations

import logging
import os.path
from calendar import month_name
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from froide.helper.breadcrumbs import Breadcrumbs, BreadcrumbView
from froide.helper.search.views import BaseSearchView

from .documents import ArticleDocument
from .filters import ArticleFilterset
from .managers import articles_visible
from .models import Article, ArticleTag, Category
from .redirect_views import ArticleRedirectView

logger = logging.getLogger(__name__)

User = get_user_model()


def get_base_breadcrumb():
    return Breadcrumbs(
        items=[(_("Articles"), reverse("blog:article-latest"))], color="blue-500"
    )


class BaseBlogView(object):
    model = Article
    namespace = "blog"

    def optimize(self, qs):
        return qs

    def get_view_url(self, kwargs=None):
        if not self.view_url_name:
            raise ImproperlyConfigured(
                "Missing `view_url_name` attribute on {0}".format(
                    self.__class__.__name__
                )
            )

        url = reverse(
            self.view_url_name,
            kwargs=kwargs or self.kwargs,
            current_app=self.namespace,
        )
        return self.request.build_absolute_uri(url)

    def get_base_queryset(self):
        return self.model.published.all()

    def get_queryset(self):
        queryset = self.get_base_queryset()
        queryset = queryset.filter(language=self.request.LANGUAGE_CODE)
        return self.optimize(queryset)

    def get_template_names(self):
        template_path = "fds_blog"
        return os.path.join(template_path, self.base_template_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(order__lt=10)
        return context


class BaseBlogListView(BaseBlogView):
    context_object_name = "article_list"
    base_template_name = "article_list.html"

    def optimize(self, qs):
        return qs.prefetch_related("categories", "categories__translations")

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["article_count"] = self.get_queryset().count()
        return context

    def get_paginate_by(self, queryset):
        return 12


class ArticleDetailView(BaseBlogView, DetailView, BreadcrumbView):
    base_template_name = "article_detail.html"
    slug_field = "slug"
    view_url_name = "blog:article-detail"

    def get_base_queryset(self):
        if (
            not getattr(self.request, "toolbar", False)
            or not self.request.toolbar.edit_mode_active
        ):
            return articles_visible(self.model._default_manager.all())
        return self.model._default_manager.all()

    def optimize(self, qs):
        return qs.prefetch_related(
            "categories", "categories__translations", "authors", "authors__user"
        )

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(
            start_publication__year=self.kwargs["year"],
            start_publication__month=self.kwargs["month"],
        )

        return self.optimize(qs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.request.article = self.object
        if hasattr(self.request, "toolbar"):
            self.request.toolbar.set_object(self.object)

        if "category" in self.kwargs:
            if self.object.first_category.slug != self.kwargs["category"]:
                return redirect(self.object.get_absolute_url())

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, object=None):
        context = super().get_context_data(object=object)
        related_articles = list(object.related.all())

        context["updated_articles"] = [
            a for a in related_articles if a.publication_date > object.publication_date
        ]
        context["previous_articles"] = [
            a for a in related_articles if a.publication_date < object.publication_date
        ]

        context["category"] = self.object.first_category

        return context

    def get_breadcrumbs(self, context):
        breadcrumbs = get_base_breadcrumb()

        category = self.object.first_category
        if category:
            breadcrumbs.items += [(category.title, category.get_absolute_url())]
            if category.color:
                breadcrumbs.color = category.color

        breadcrumbs.items += [(self.object.title, self.get_view_url())]
        return breadcrumbs


class ArticleListView(BaseBlogListView, ListView, BreadcrumbView):
    view_url_name = "blog:article-latest"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["year_filter"] = (
            self.get_queryset().dates("start_publication", "year").reverse()
        )
        context["category_filter"] = Category.objects.all().prefetch_related(
            "translations"
        )
        return context

    def get_breadcrumbs(self, context):
        return get_base_breadcrumb()


class ArticleArchiveView(BaseBlogListView, ListView, BreadcrumbView):
    date_field = "start_publication"
    allow_empty = True
    allow_future = True
    view_url_name = "blog:article-archive"

    def get_queryset(self):
        qs = super().get_queryset()
        if "month" in self.kwargs:
            qs = qs.filter(**{"%s__month" % self.date_field: self.kwargs["month"]})
        if "year" in self.kwargs:
            qs = qs.filter(**{"%s__year" % self.date_field: self.kwargs["year"]})
        qs = self.optimize(qs)

        if not qs.exists():
            raise Http404(_("No articles found"))

        return qs

    def get_context_data(self, **kwargs):
        kwargs["month"] = (
            int(self.kwargs.get("month")) if "month" in self.kwargs else None
        )
        kwargs["year"] = int(self.kwargs.get("year")) if "year" in self.kwargs else None
        if kwargs["year"]:
            kwargs["archive_date"] = now().replace(
                kwargs["year"], kwargs["month"] or 1, 1
            )

        context = super().get_context_data(**kwargs)

        if kwargs["year"] and not kwargs["month"]:
            context["month_filter"] = self.get_queryset().dates(
                "start_publication", "month"
            )

        return context

    def get_breadcrumbs(self, context):
        breadcrumbs = get_base_breadcrumb()

        if "year" in self.kwargs:
            breadcrumbs.items += [
                (
                    context["year"],
                    self.get_view_url({"year": context["year"]}),
                )
            ]
            if "month" in self.kwargs:
                breadcrumbs.items += [
                    (
                        _(month_name[context["month"]]),
                        self.get_view_url(
                            {"year": context["year"], "month": context["month"]}
                        ),
                    )
                ]

        return breadcrumbs


class TaggedListView(BaseBlogListView, ListView, BreadcrumbView):
    view_url_name = "blog:article-tagged"

    def get_queryset(self):
        self.tag = get_object_or_404(ArticleTag, slug=self.kwargs["tag"])
        qs = super().get_queryset()
        return self.optimize(qs.filter(tags=self.tag))

    def get_context_data(self, **kwargs):
        kwargs["article_tag"] = self.tag
        context = super().get_context_data(**kwargs)
        return context

    def get_breadcrumbs(self, context):
        return get_base_breadcrumb() + [
            (_("Tag “%s”") % self.tag.name, self.get_view_url())
        ]


class AuthorArticleView(BaseBlogListView, ListView, BreadcrumbView):
    view_url_name = "blog:article-author"

    def get_queryset(self):
        qs = super().get_queryset()
        if "username" in self.kwargs:
            qs = qs.filter(authors__user__username=self.kwargs["username"])
        return self.optimize(qs)

    def get_context_data(self, **kwargs):
        self.author = get_object_or_404(User, username=self.kwargs.get("username"))
        kwargs["author"] = self.author
        context = super().get_context_data(**kwargs)
        return context

    def get_breadcrumbs(self, context):
        return get_base_breadcrumb() + [
            _("Authors"),
            (self.author.get_full_name(), self.get_view_url()),
        ]


def root_slug_view(request, category):
    slug = category  # to avoid confusion

    category = Category.objects.active_translations(get_language(), slug=slug)

    if category.exists():
        return CategoryArticleView.as_view(category=category.get())(
            request, category=slug
        )

    return redirect(ArticleRedirectView().get_redirect_url(slug=slug))


class CategoryArticleView(BaseBlogListView, ListView, BreadcrumbView):
    _category = None
    view_url_name = "blog:article-category"

    def __init__(self, *args, **kwargs):
        if "category" in kwargs:
            self._category = kwargs["category"]

        super(CategoryArticleView, self).__init__()

    @property
    def category(self):
        if not self._category:
            try:
                self._category = Category.objects.active_translations(
                    get_language(), slug=self.kwargs["category"]
                ).get()
            except Category.DoesNotExist:
                raise Http404
        return self._category

    def get(self, *args, **kwargs):
        # submit object to cms toolbar to get correct language switcher behavior
        if hasattr(self.request, "toolbar"):
            self.request.toolbar.set_object(self.category)
        return super().get(*args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        if "category" in self.kwargs:
            qs = qs.filter(categories=self.category.pk)
        return self.optimize(qs)

    def get_context_data(self, **kwargs):
        kwargs["category"] = self.category
        context = super().get_context_data(**kwargs)
        return context

    def get_breadcrumbs(self, context):
        breadcrumbs = get_base_breadcrumb()
        breadcrumbs.items += [(self.category.title, self.get_view_url())]

        if self.category.color:
            breadcrumbs.color = self.category.color

        return breadcrumbs


class ArticleSearchView(BaseSearchView, BreadcrumbView):
    search_name = "blog"
    template_name = "fds_blog/search.html"
    object_template = "fds_blog/result_item.html"
    model = Article
    document = ArticleDocument
    filterset = ArticleFilterset
    search_url_name = "blog:article-search"
    default_sort = "_score"
    show_filters = {"category", "author"}
    has_facets = True
    facet_config = {
        "category": {
            "model": Category,
            "getter": lambda x: str(x["object"].id),
            "label_getter": lambda x: x["object"].title,
            "label": _("categories"),
        }
    }

    def get_breadcrumbs(self, context):
        return get_base_breadcrumb() + [_("Search")]
