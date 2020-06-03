from django import forms
from django.utils.translation import gettext_lazy as _

import django_filters

from froide.helper.search.filters import BaseSearchFilterSet

from .models import Category, Author


class ArticleFilterset(BaseSearchFilterSet):
    query_fields = ['title^5', 'description^3', 'content']

    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        empty_label=_('all categories'),
        widget=forms.Select(
            attrs={
                'label': _('category'),
                'class': 'form-control'
            }
        ),
        method='filter_category'
    )

    author = django_filters.ModelChoiceFilter(
        queryset=Author.objects.all(),
        empty_label=_('all authors'),
        widget=forms.Select(
            attrs={
                'label': _('author'),
                'class': 'form-control'
            }
        ),
        method='filter_author'
    )

    def filter_category(self, qs, name, value):
        return qs.filter(category=value.id)

    def filter_author(self, qs, name, value):
        return qs.filter(author=value.id)
