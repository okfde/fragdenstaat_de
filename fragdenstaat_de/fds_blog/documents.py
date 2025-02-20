"""
Adapted from
https://github.com/divio/aldryn-search/blob/master/aldryn_search/search_indexes.py
"""

from django.utils.html import strip_tags

from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from froide.helper.search import (
    get_index,
    get_search_analyzer,
    get_search_quote_analyzer,
    get_text_analyzer,
)
from froide.helper.tasks import search_instance_delete, search_instance_save

from .models import Article

index = get_index("article")

analyzer = get_text_analyzer()
search_analyzer = get_search_analyzer()
search_quote_analyzer = get_search_quote_analyzer()


@registry.register_document
@index.document
class ArticleDocument(Document):
    title = fields.TextField(
        fields={"raw": fields.KeywordField()},
        search_analyzer=search_analyzer,
        search_quote_analyzer=search_quote_analyzer,
        analyzer=analyzer,
    )
    url = fields.TextField(
        fields={"raw": fields.KeywordField()},
        analyzer=analyzer,
    )
    description = fields.TextField(
        fields={"raw": fields.KeywordField()},
        search_analyzer=search_analyzer,
        search_quote_analyzer=search_quote_analyzer,
        analyzer=analyzer,
    )
    start_publication = fields.DateField()
    author = fields.ListField(fields.TextField())
    category = fields.ListField(fields.IntegerField())

    content = fields.TextField(
        analyzer=analyzer,
        search_analyzer=search_analyzer,
        search_quote_analyzer=search_quote_analyzer,
        index_options="offsets",
    )

    special_signals = True

    class Django:
        model = Article
        queryset_chunk_size = 100

    def get_queryset(self):
        return Article.published.all()

    def prepare_content(self, obj):
        html = obj.get_html_content()
        return " ".join(
            [obj.title, strip_tags(obj.description), strip_tags(html)]
            + [o.title for o in obj.categories.all()]
            + [t.name for t in obj.tags.all()]
            + [str(a) for a in obj.authors.all()]
        )

    def prepare_description(self, obj):
        return strip_tags(obj.description)

    def prepare_url(self, obj):
        return obj.get_absolute_url()

    def prepare_title(self, obj):
        return obj.title

    def prepare_start_publication(self, obj):
        return obj.start_publication

    def prepare_category(self, obj):
        cats = obj.categories.all()
        return [o.id for o in cats]

    def prepare_author(self, obj):
        authors = obj.authors.all()
        return [o.get_full_name() for o in authors]


def index_article(article):
    if article.is_visible:
        search_instance_save.delay(article._meta.label_lower, article.pk)
    else:
        search_instance_delete.delay(article._meta.label_lower, article.pk)
