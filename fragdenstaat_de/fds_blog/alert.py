from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from froide.helper.search.queryset import SearchQuerySetWrapper
from froide.helper.utils import update_query_params
from froide.searchalert.configuration import AlertConfiguration, AlertEvent


class ArticleAlertConfiguration(AlertConfiguration):
    key = "article"
    title = _("Investigations and articles")

    @classmethod
    def search(cls, query, start_date, item_count=5) -> list[AlertEvent]:
        from .documents import ArticleDocument
        from .filters import ArticleFilterset
        from .models import Article

        s = ArticleDocument.search()
        s = s.highlight_options(encoder="html", number_of_fragments=10).highlight(
            "content"
        )
        s = s.sort("-start_publication")
        sqs = SearchQuerySetWrapper(s, Article)

        filtered = ArticleFilterset(
            {
                "q": query,
                "start_publication_after": start_date.date().strftime("%Y-%m-%d"),
            },
            queryset=sqs,
        )
        sqs = filtered.qs
        count = sqs.count()
        qs = sqs.to_queryset()
        qs = qs[:item_count]
        queryset = sqs.wrap_queryset(qs)

        return (
            count,
            [
                AlertEvent(
                    title=article.title,
                    url=article.get_full_url(),
                    content=article.query_highlight,
                )
                for article in queryset
            ],
        )

    @classmethod
    def get_search_link(cls, query, start_date) -> str:
        base_url = settings.SITE_URL + reverse("blog:article-search")
        return update_query_params(
            base_url,
            {
                "q": query,
                "start_publication_after": start_date.date().strftime("%Y-%m-%d"),
                "sort": "-start_publication",
            },
        )
