import pytest

from fragdenstaat_de.theme.tests.data.search_queries import (
    exact_phrase_search_tests,
    search_tests,
)
from fragdenstaat_de.theme.tests.data.search_tokens import (
    search_analyzer_tests,
    search_quote_analyzer_tests,
    text_analyzer_tests,
)


class TestElasticsearchAnalyzers:
    @pytest.mark.parametrize(
        "text, tokens", text_analyzer_tests, ids=[t[0] for t in text_analyzer_tests]
    )
    def test_text_analyzer_tokens(self, analyze, text, tokens):
        assert analyze("fds_analyzer", text) == tokens

    @pytest.mark.parametrize(
        "text, tokens", search_analyzer_tests, ids=[t[0] for t in search_analyzer_tests]
    )
    def test_search_analyzer_tokens(self, analyze, text, tokens):
        assert analyze("fds_search_analyzer", text) == tokens

    @pytest.mark.parametrize(
        "text, tokens",
        search_quote_analyzer_tests,
        ids=[t[0] for t in search_quote_analyzer_tests],
    )
    def test_search_quote_analyzer_tokens(self, analyze, text, tokens):
        assert analyze("fds_search_quote_analyzer", text) == tokens


class TestElasticsearchSearch:
    @pytest.mark.parametrize(
        "query_text, doc_ids, highlights",
        search_tests,
        ids=[q[0] for q in search_tests],
    )
    def test_search(self, search, query_text, doc_ids, highlights):
        res_doc_ids, res_highlights = search(query_text)

        assert res_doc_ids == doc_ids
        assert res_highlights == highlights

    @pytest.mark.parametrize(
        ("query_text", "doc_ids", "highlights"),
        exact_phrase_search_tests,
        ids=[q[0] for q in exact_phrase_search_tests],
    )
    def test_exact_phrase_search(self, search, query_text, doc_ids, highlights):
        # Add quotes to search for exact phrase.
        query_text = f'"{query_text}"'
        res_doc_ids, res_highlights = search(query_text)

        assert res_doc_ids == doc_ids
        assert res_highlights == highlights
