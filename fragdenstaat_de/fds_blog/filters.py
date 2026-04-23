from django.utils.translation import gettext_lazy as _

import django_filters
from django_filters.widgets import DateRangeWidget
from elasticsearch_dsl.query import Q as ESQ

from froide.helper.search.filters import BaseSearchFilterSet
from froide.helper.widgets import BootstrapSelect

from .models import Author, Category


class ArticleFilterset(BaseSearchFilterSet):
    query_fields = ["title^5", "description^3", "content"]

    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        empty_label=_("all categories"),
        widget=BootstrapSelect(attrs={"label": _("category")}),
        method="filter_category",
    )

    author = django_filters.ModelChoiceFilter(
        queryset=Author.objects.all(),
        empty_label=_("all authors"),
        widget=BootstrapSelect(attrs={"label": _("author")}),
        method="filter_author",
    )

    start_publication = django_filters.DateFromToRangeFilter(
        method="filter_start_publication",
        widget=DateRangeWidget,
    )

    sort = django_filters.ChoiceFilter(
        choices=[
            ("-start_publication", _("Publication date (newest first)")),
            ("start_publication", _("Publication date (oldest first)")),
        ],
        label=_("sort"),
        empty_label=_("default sort"),
        widget=BootstrapSelect,
        method="add_sort",
    )

    def filter_category(self, qs, name, value):
        return qs.filter(category=value.id)

    def filter_author(self, qs, name, value):
        return qs.filter(author=value.id)

    def filter_start_publication(self, qs, name, value):
        range_kwargs = {}
        if value.start is not None:
            range_kwargs["gte"] = value.start
        if value.stop is not None:
            range_kwargs["lte"] = value.stop

        return self.apply_filter(qs, name, ESQ("range", created_at=range_kwargs))

    def add_sort(self, qs, name, value):
        if value:
            return qs.add_sort(value)
        return qs
