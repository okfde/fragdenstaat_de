import logging

from django.core.exceptions import MultipleObjectsReturned
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language
from django.views.generic import RedirectView

from .models import Article

logger = logging.getLogger(__name__)


class ArticleRedirectView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if "pk" in kwargs:
            qs = {"pk": kwargs["pk"]}
        else:
            qs = {"slug": kwargs["slug"], "language": get_language()}

            optional_specifiers = [
                ("year", "start_publication__year"),
                ("month", "start_publication__month"),
                ("day", "start_publication__day"),
                ("category", "categories__translations__slug"),
            ]

            for kwargs_key, filter_key in optional_specifiers:
                if kwargs_key in kwargs:
                    qs[filter_key] = kwargs[kwargs_key]

        try:
            article = get_object_or_404(Article.published, **qs)
            return article.get_absolute_url()
        except MultipleObjectsReturned:
            # url not specific enough
            logger.error("Ambiguous article urls at %s", self.request.path)
            raise Http404


class CategoryRedirectView(RedirectView):
    permanent = True
    pattern_name = "blog:article-category"


class TagRedirectView(RedirectView):
    permanent = True
    pattern_name = "blog:article-tagged"


class AuthorRedirectView(RedirectView):
    permanent = True
    pattern_name = "blog:article-author"


class ArchiveRedirectView(RedirectView):
    permanent = True
    pattern_name = "blog:article-archive"


class SearchRedirectView(RedirectView):
    pattern_name = "blog:article-search"
    permanent = True
    query_string = True
