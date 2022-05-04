"""
Adapted from
https://github.com/divio/aldryn-search/blob/master/aldryn_search/search_indexes.py
"""

from django.conf import settings
from django.db.models import Q
from django.utils import timezone, translation
from django.utils.html import strip_tags

from cms.models import Title
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
    )
    url = fields.TextField(
        fields={"raw": fields.KeywordField()},
        analyzer=analyzer,
    )
    description = fields.TextField(
        fields={"raw": fields.KeywordField()},
        analyzer=analyzer,
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
        model = Title
        queryset_chunk_size = 100

    def get_queryset(self):
        now = timezone.now()
        queryset = (
            Title.objects.public()
            .filter(
                Q(page__publication_date__lt=now)
                | Q(page__publication_date__isnull=True),
                Q(page__publication_end_date__gte=now)
                | Q(page__publication_end_date__isnull=True),
                Q(redirect__exact="") | Q(redirect__isnull=True),
            )
            .select_related("page")
        )

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

    def get_page_placeholders(self, page):
        """
        In the project settings set up the variable
        PLACEHOLDERS_SEARCH_LIST = {
            # '*' is mandatory if you define at least one slot rule
            '*': {
                'include': [ 'slot1', 'slot2', etc. ],
                'exclude': [ 'slot3', 'slot4', etc. ],
            }
            'reverse_id_alpha': {
                'include': [ 'slot1', 'slot2', etc. ],
                'exclude': [ 'slot3', 'slot4', etc. ],
            },
            'reverse_id_beta': {
                'include': [ 'slot1', 'slot2', etc. ],
                'exclude': [ 'slot3', 'slot4', etc. ],
            },
            'reverse_id_only_include': {
                'include': [ 'slot1', 'slot2', etc. ],
            },
            'reverse_id_only_exclude': {
                'exclude': [ 'slot3', 'slot4', etc. ],
            },
            # exclude it from the placehoders search list
            # (however better to remove at all to exclude it)
            'reverse_id_empty': []
            etc.
        }
        or leave it empty
        PLACEHOLDERS_SEARCH_LIST = {}
        """
        reverse_id = page.reverse_id
        args = []
        kwargs = {}

        placeholders_by_page = getattr(settings, "PLACEHOLDERS_SEARCH_LIST", {})

        if placeholders_by_page:
            filter_target = None
            excluded = []
            slots = []
            if "*" in placeholders_by_page:
                filter_target = "*"
            if reverse_id and reverse_id in placeholders_by_page:
                filter_target = reverse_id
            if not filter_target:
                raise AttributeError(
                    "Leave PLACEHOLDERS_SEARCH_LIST empty or set up at least the generic handling"
                )
            if "include" in placeholders_by_page[filter_target]:
                slots = placeholders_by_page[filter_target]["include"]
            if "exclude" in placeholders_by_page[filter_target]:
                excluded = placeholders_by_page[filter_target]["exclude"]
            diff = set(slots) - set(excluded)
            if diff:
                kwargs["slot__in"] = diff
            else:
                args.append(~Q(slot__in=excluded))
        return page.placeholders.filter(*args, **kwargs)

    def get_search_data(self, obj, language, request):
        current_page = obj.page

        MAX_CHARS = 1024 * 400  # 400 kb text

        text_bits = []
        context = SekizaiContext(request)
        context["request"] = request
        placeholders = self.get_page_placeholders(current_page)
        for placeholder in placeholders:
            text_bits.append(
                strip_tags(render_placeholder(context, placeholder)[:MAX_CHARS])
            )

        page_meta_description = current_page.get_meta_description(
            fallback=False, language=language
        )

        if page_meta_description:
            text_bits.append(page_meta_description)

        page_meta_keywords = getattr(current_page, "get_meta_keywords", None)

        if callable(page_meta_keywords):
            text_bits.append(page_meta_keywords())
        return clean_join(" ", text_bits)
