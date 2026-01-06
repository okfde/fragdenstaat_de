import re

import pytest
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Document, Text

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


class TestDocument(Document):
    content = Text(
        analyzer=get_text_analyzer(),
        search_analyzer=get_search_analyzer(),
        search_quote_analyzer=get_search_quote_analyzer(),
        index_options="offsets",
    )

    class Django:
        model = Article


@pytest.fixture(scope="session")
def elasticsearch_client():
    return Elasticsearch("http://localhost:9200")


@pytest.fixture(scope="session")
def test_index(elasticsearch_client):
    # Set up the test index.
    index = get_index("docs")
    index.document(TestDocument)
    # Timeout has to be set here - is ignored when set in Elasticsearch().
    index.create(timeout="60s")

    # Create test documents.
    for doc in search_docs:
        doc_id = doc.get("id")
        TestDocument(**doc).save(id=doc_id)

    TestDocument._index.refresh()

    yield index

    # Clean up after the test run.
    index.delete()


@pytest.fixture(scope="session")
def analyze(test_index):
    def _analyze(analyzer_name, text):
        result = test_index.analyze(
            body={"analyzer": analyzer_name, "text": text},
        )

        return [t["token"] for t in result["tokens"]]

    return _analyze


@pytest.fixture(scope="session")
def test_search_filterset():
    class TestSearchFilterSet(BaseSearchFilterSet):
        query_fields = ["content"]

    return TestSearchFilterSet


@pytest.fixture(scope="session")
def search(test_index, test_search_filterset):
    def _search(query):
        data = {}
        if query:
            data["q"] = query

        mock_model = type(
            "MockModel",
            (),
            {"_default_manager": type("Manager", (), {"all": lambda: None})},
        )

        search = test_index.search()
        search = search.highlight_options(encoder="html").highlight("content")

        sqs = SearchQuerySetWrapper(search, mock_model)
        filterset = test_search_filterset(data=data, queryset=sqs)

        results = list(filterset.qs)

        return transform_search_results(results)

    return _search


def transform_search_results(search_results):
    """
    Transform the raw Elasticsearch result into a more convenient format.

    Return a tuple of (`doc_ids`, `highlights`), where:
    - `doc_ids` is a list of document IDs that matched the query (in the order they were returned).
    - `highlights` is a list of lists, where each inner list contains the highlighted
      snippets for the corresponding document.
    """
    doc_ids = [hit.meta.id for hit in search_results]
    highlights = get_highlights(search_results)

    return doc_ids, highlights


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
