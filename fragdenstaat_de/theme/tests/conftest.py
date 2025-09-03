import re

from django.conf import settings

import pytest
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Index

from fragdenstaat_de.theme.search import (
    get_search_analyzer,
    get_search_quote_analyzer,
    get_text_analyzer,
)
from fragdenstaat_de.theme.tests.data.search_docs import search_docs

ES_CONFIG = settings.ELASTICSEARCH_DSL["default"]


@pytest.fixture(scope="session")
def elasticsearch_client():
    return Elasticsearch(hosts=ES_CONFIG["hosts"])


@pytest.fixture(scope="session")
def test_index(elasticsearch_client):
    index_name = "test_fds_analyzers"
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
def search(elasticsearch_client, test_index, test_documents):
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

        return transform(result)

    return _search


def transform(search_result):
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
