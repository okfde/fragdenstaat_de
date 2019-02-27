'''
Adapted from
https://github.com/divio/aldryn-search/blob/master/aldryn_search/search_indexes.py
'''

from django.utils.html import strip_tags

from django_elasticsearch_dsl import DocType, fields

from froide.helper.search import (
    get_index, get_text_analyzer
)

from .models import Article


index = get_index('article')

analyzer = get_text_analyzer()


@index.doc_type
class ArticleDocument(DocType):
    title = fields.TextField(
        fields={'raw': fields.KeywordField()},
        analyzer=analyzer,
    )
    url = fields.TextField(
        fields={'raw': fields.KeywordField()},
        analyzer=analyzer,
    )
    description = fields.TextField(
        fields={'raw': fields.KeywordField()},
        analyzer=analyzer,
    )
    start_publication = fields.DateField()
    author = fields.ListField(fields.IntegerField())
    category = fields.ListField(fields.IntegerField())

    content = fields.TextField(
        analyzer=analyzer
    )

    class Meta:
        model = Article
        queryset_chunk_size = 100

    def get_queryset(self):
        return Article.published.all()

    def prepare_content(self, obj):
        html = obj.get_html_content()
        return strip_tags(html)

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
        return [o.id for o in authors]
