"""
Adapted from
https://github.com/divio/aldryn-search/blob/master/aldryn_search/search_indexes.py
"""

from django.db.models import Q
from django.utils import translation
from django.utils.html import strip_tags

from cms.models import PageContent
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from sekizai.context import SekizaiContext

from froide.helper.search import (
    get_index,
    get_search_analyzer,
    get_search_quote_analyzer,
    get_text_analyzer,
)

from .utils import clean_join, get_request, render_placeholder

index = get_index("cmspage")

analyzer = get_text_analyzer()
search_analyzer = get_search_analyzer()
search_quote_analyzer = get_search_quote_analyzer()


@registry.register_document
@index.document
class CMSDocument(Document):
    title = fields.TextField(
        fields={"raw": fields.KeywordField()},
        analyzer=analyzer,
        search_analyzer=search_analyzer,
        search_quote_analyzer=search_quote_analyzer,
    )
    url = fields.TextField(
        fields={"raw": fields.KeywordField()},
        analyzer=analyzer,
    )
    description = fields.TextField(
        fields={"raw": fields.KeywordField()},
        analyzer=analyzer,
        search_analyzer=search_analyzer,
        search_quote_analyzer=search_quote_analyzer,
    )

    content = fields.TextField(
        analyzer=analyzer,
        search_analyzer=search_analyzer,
        search_quote_analyzer=search_quote_analyzer,
        index_options="offsets",
    )
    language = fields.KeywordField()

    special_signals = True

    class Django:
        model = PageContent
        queryset_chunk_size = 100

    def get_queryset(self):
        queryset = PageContent.objects.filter(
            Q(redirect__exact="") | Q(redirect__isnull=True),
        ).select_related("page")

        queryset = queryset.select_related("page__node")
        return queryset.distinct()

    def prepare_content(self, obj):
        current_language = obj.language
        request = get_request(obj.language)
        with translation.override(obj.language):
            content = self.get_search_data(obj, current_language, request)
        return content

    def prepare_description(self, obj):
        return obj.meta_description or ""

    def prepare_url(self, obj):
        with translation.override(obj.language):
            return obj.page.get_absolute_url(language=obj.language)

    def prepare_title(self, obj):
        return obj.title

    def prepare_language(self, obj):
        return obj.language

    def get_search_data(self, obj, language, request):
        MAX_CHARS = 1024 * 400  # 400 kb text
        text_bits = []
        current_page = obj.page
        context = SekizaiContext(request)
        context["request"] = request

        placeholders = current_page.get_placeholders(language)
        for placeholder in placeholders:
            text_bits.append(
                strip_tags(render_placeholder(context, placeholder))[:MAX_CHARS]
            )

        page_meta_description = current_page.get_meta_description(
            fallback=False, language=language
        )

        if page_meta_description:
            text_bits.append(page_meta_description)

        return clean_join(" ", text_bits)
