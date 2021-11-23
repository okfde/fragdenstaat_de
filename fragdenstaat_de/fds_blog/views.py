import os.path

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from django.utils.translation import get_language
from django.views.generic import DetailView, ListView
from django.utils.translation import gettext_lazy as _

from froide.helper.search.views import BaseSearchView

from .documents import ArticleDocument
from .models import Category, Article, ArticleTag
from .filters import ArticleFilterset
from .managers import articles_visible

User = get_user_model()


class BaseBlogView(object):
    model = Article

    def optimize(self, qs):
        return qs

    def get_view_url(self):
        if not self.view_url_name:
            raise ImproperlyConfigured(
                "Missing `view_url_name` attribute on {0}".format(
                    self.__class__.__name__
                )
            )

        url = reverse(
            self.view_url_name,
            args=self.args,
            kwargs=self.kwargs,
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

    def get_paginate_by(self, queryset):
        return 12


class ArticleDetailView(BaseBlogView, DetailView):
    base_template_name = "article_detail.html"
    slug_field = "slug"
    view_url_name = "fds_blog:article-detail"

    def get_base_queryset(self):
        if (
            not getattr(self.request, "toolbar", False)
            or not self.request.toolbar.edit_mode_active
        ):
            return articles_visible(self.model._default_manager.all())
        return self.model._default_manager.all()

    def optimize(self, qs):
        return qs.prefetch_related("categories", "authors")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.request.article = self.object
        if hasattr(self.request, "toolbar"):
            self.request.toolbar.set_object(self.object)

        if self.object.language != request.LANGUAGE_CODE:
            queryset = self.get_queryset()
            if self.object.uuid is not None:
                queryset = queryset.filter(
                    uuid=self.object.uuid, language=request.LANGUAGE_CODE
                )
                try:
                    self.object = queryset.get()
                except Article.DoesNotExist:
                    raise Http404
                return redirect(self.object, permanent=True)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, object=None):
        ctx = super().get_context_data(object=object)
        related_articles = list(object.related.all())

        ctx["updated_articles"] = [
            a for a in related_articles if a.publication_date < object.publication_date
        ]
        ctx["previous_articles"] = [
            a for a in related_articles if a.publication_date > object.publication_date
        ]
        return ctx


class ArticleListView(BaseBlogListView, ListView):
    view_url_name = "fds_blog:article-latest"

    def get_queryset(self):
        qs = super().get_queryset()

        self.featured = None
        page = self.request.GET.get("page", None)
        if not page or page == "1":
            try:
                self.featured = qs.filter(date_featured__isnull=False).order_by(
                    "-date_featured"
                )[0]
            except IndexError:
                pass

        if self.featured is not None:
            qs = qs.exclude(pk=self.featured.pk)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["featured"] = self.featured
        return context


class ArticleArchiveView(BaseBlogListView, ListView):
    date_field = "start_publication"
    allow_empty = True
    allow_future = True
    view_url_name = "fds_blog:article-archive"

    def get_queryset(self):
        qs = super().get_queryset()
        if "month" in self.kwargs:
            qs = qs.filter(**{"%s__month" % self.date_field: self.kwargs["month"]})
        if "year" in self.kwargs:
            qs = qs.filter(**{"%s__year" % self.date_field: self.kwargs["year"]})
        return self.optimize(qs)

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
        return context


class TaggedListView(BaseBlogListView, ListView):
    view_url_name = "fds_blog:article-tagged"

    def get_queryset(self):
        self.tag = get_object_or_404(ArticleTag, slug=self.kwargs["tag"])
        qs = super().get_queryset()
        return self.optimize(qs.filter(tags=self.tag))

    def get_context_data(self, **kwargs):
        kwargs["article_tag"] = self.tag
        context = super().get_context_data(**kwargs)
        return context


class AuthorArticleView(BaseBlogListView, ListView):
    view_url_name = "fds_blog:article-author"

    def get_queryset(self):
        qs = super().get_queryset()
        if "username" in self.kwargs:
            qs = qs.filter(authors__user__username=self.kwargs["username"])
        return self.optimize(qs)

    def get_context_data(self, **kwargs):
        kwargs["author"] = get_object_or_404(User, username=self.kwargs.get("username"))
        context = super().get_context_data(**kwargs)
        return context


class CategoryArticleView(BaseBlogListView, ListView):
    _category = None
    view_url_name = "fds_blog:article-category"

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


class ArticleSearchView(BaseSearchView):
    search_name = "blog"
    template_name = "fds_blog/search.html"
    object_template = "fds_blog/result_item.html"
    model = Article
    document = ArticleDocument
    filterset = ArticleFilterset
    search_url_name = "blog:article-search"
    default_sort = "-start_publication"
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
