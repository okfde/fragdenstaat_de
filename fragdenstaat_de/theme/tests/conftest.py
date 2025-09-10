import re

from django.conf import settings

import pytest
from django_elasticsearch_dsl.registries import registry
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Document, Index, Text

from froide.helper.search import (
    SearchQuerySetWrapper,
    get_index,
    get_search_analyzer,
    get_search_quote_analyzer,
    get_text_analyzer,
)
from froide.helper.search.filters import BaseSearchFilterSet

from fragdenstaat_de.fds_blog.models import Article
from fragdenstaat_de.theme.tests.testdata.search_docs import search_docs

ES_CONFIG = settings.ELASTICSEARCH_DSL["default"]


@pytest.fixture(scope="session")
def elasticsearch_client():
    return Elasticsearch(hosts=ES_CONFIG["hosts"])


@pytest.fixture(scope="session")
def test_index(elasticsearch_client):
    index_name = "test_index"
    index = Index(index_name, using=elasticsearch_client)

    index.analyzer(get_text_analyzer())
    index.analyzer(get_search_analyzer())
    index.analyzer(get_search_quote_analyzer())

    index.create()

    yield index_name

    index.delete()


@pytest.fixture(scope="session")
def analyze(elasticsearch_client, test_index):
    def _analyze(analyzer_name, text):
        result = elasticsearch_client.indices.analyze(
            index=test_index, body={"analyzer": analyzer_name, "text": text}
        )

        return [t["token"] for t in result["tokens"]]

    return _analyze


@pytest.fixture(scope="session")
def test_documents(elasticsearch_client, test_index):
    elasticsearch_client.indices.put_mapping(
        index=test_index,
        body={
            "properties": {
                "content": {
                    "type": "text",
                    "analyzer": "fds_analyzer",
                    "search_analyzer": "fds_search_analyzer",
                    "search_quote_analyzer": "fds_search_quote_analyzer",
                }
            }
        },
    )

    for doc in search_docs:
        elasticsearch_client.index(
            index=test_index, id=doc["id"], body=doc, refresh=True
        )

    return search_docs


@pytest.fixture(scope="session")
def es_search(elasticsearch_client, test_index, test_documents):
    def _search(query_text):
        body = {
            "query": {
                "simple_query_string": {
                    "query": query_text,
                    "fields": ["content"],
                    "default_operator": "and",
                    "lenient": True,
                },
            },
            "highlight": {"fields": {"content": {}}},
        }

        result = elasticsearch_client.search(index=test_index, body=body)

        return transform_es_search_result(result)

    return _search


def transform_es_search_result(search_result):
    """
    Transform the raw Elasticsearch result into a more convenient format.

    Return a tuple of (`doc_ids`, `highlights`), where:
    - `hit_ids` is a list of document IDs that matched the query (in the order they were returned).
    - `highlights` is a list of lists, where each inner list contains the highlighted
      snippets for the corresponding document.
    """
    hits = search_result["hits"]["hits"]
    doc_ids = [hit["_id"] for hit in hits]
    highlighted_texts = [hit.get("highlight", {}).get("content", []) for hit in hits]
    highlights = [
        re.findall(r"<em>(.*?)</em>", " ".join(texts)) for texts in highlighted_texts
    ]

    return doc_ids, highlights


@pytest.fixture(scope="session")
def test_document_class(elasticsearch_client):
    index = get_index("test_index")
    analyzer = get_text_analyzer()
    search_analyzer = get_search_analyzer()
    search_quote_analyzer = get_search_quote_analyzer()

    @registry.register_document
    @index.document
    class TestDocument(Document):
        content = Text(
            analyzer=analyzer,
            search_analyzer=search_analyzer,
            search_quote_analyzer=search_quote_analyzer,
            index_options="offsets",
        )

        class Django:
            model = Article

    index.create()

    yield TestDocument

    index.delete()


@pytest.fixture(scope="session")
def create_test_documents(test_document_class):
    docs = []
    for doc in search_docs:
        doc_id = doc.get("id")
        doc_obj = test_document_class(**doc)
        doc_obj.save(id=doc_id)
        docs.append(doc_obj)

    test_document_class._index.refresh()

    return docs


@pytest.fixture(scope="session")
def test_search_filterset():
    class TestSearchFilterSet(BaseSearchFilterSet):
        query_fields = ["content"]

    return TestSearchFilterSet


@pytest.fixture(scope="session")
def search(test_document_class, create_test_documents, test_search_filterset):
    def _search(query):
        data = {}
        if query:
            data["q"] = query

        mock_model = type(
            "MockModel",
            (),
            {"_default_manager": type("Manager", (), {"all": lambda: None})},
        )

        search = test_document_class.search()
        search = search.highlight_options(encoder="html").highlight("content")

        sqs = SearchQuerySetWrapper(search, mock_model)
        filterset = test_search_filterset(data=data, queryset=sqs)

        results = list(filterset.qs)

        return transform_search_result(results)

    return _search


def transform_search_result(search_results):
    ids = [hit.meta.id for hit in search_results]
    highlights = get_highlights(search_results)

    return ids, highlights


def get_highlights(search_results):
    highlighted_texts = []
    for hit in search_results:
        if hasattr(hit.meta, "highlight") and hasattr(hit.meta.highlight, "content"):
            highlighted_texts.append(hit.meta.highlight.content)
        else:
            highlighted_texts.append([])

    highlights = [
        re.findall(r"<em>(.*?)</em>", " ".join(texts)) for texts in highlighted_texts
    ]

    return highlights
