import pytest

from fragdenstaat_de.theme.search import QueryPreprocessor, get_decompounder_analyzer
from fragdenstaat_de.theme.tests.testdata.search_queries import (
    exact_phrase_search_tests,
    search_tests,
)
from fragdenstaat_de.theme.tests.testdata.search_tokens import (
    decompounder_analyzer_tests,
    search_analyzer_tests,
    search_quote_analyzer_tests,
    text_analyzer_tests,
)


@pytest.mark.elasticsearch
class TestSearchFilterSet:
    """
    Tests for a realistic search scenario using the BaseSearchFilterSet with preprocessing.
    """

    @pytest.mark.parametrize(
        "query_text, doc_ids, highlights",
        search_tests,
        ids=[q[0] for q in search_tests],
    )
    def test_search(self, search, query_text, doc_ids, highlights):
        res_doc_ids, res_highlights = search(query=query_text)

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


@pytest.mark.elasticsearch
class TestElasticsearchAnalyzers:
    """
    Tests for directly testing the output of the analyzers (tokens) in Elasticsearch.
    """

    @pytest.mark.parametrize(
        "text, tokens",
        decompounder_analyzer_tests,
        ids=[t[0] for t in decompounder_analyzer_tests],
    )
    def test_decompounder_analyzer_tokens(self, text, tokens):
        decompounder = get_decompounder_analyzer()
        result = decompounder.simulate(text)
        result_tokens = [t.token for t in result.tokens]

        assert result_tokens == tokens

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


test_cases = [
    ("Informationsfreiheit", "(information freiheit)"),
    (
        "Informationsfreiheitsgesetze",
        "(information freiheit gesetz)",
    ),
    ("Fußgängerübergang", "(fuss gang uber gang)"),
    (
        'Ministerium "Kleine Anfrage"',
        'Ministerium "Kleine Anfrage"',
    ),
    ("Anfrage -Ministerium", "Anfrage -Ministerium"),
    ("Götersloh~1", "Götersloh~1"),
    ('"Zugang Informationen"~1', '"Zugang Informationen"~1'),
    ("Informationsfr*", "Informationsfr*"),
    ("die Stadt", "die Stadt"),
    ("Hund | Maus", "Hund | Maus"),
    ("Hund + Maus", "Hund + Maus"),
    (
        "Güterverkehr Informationsfreiheit",
        "(gut verkehr) (information freiheit)",
    ),
    (
        "Hund Informationsfreiheit",
        "Hund (information freiheit)",
    ),
    (
        "Hund | Informationsfreiheit",
        "Hund | (information freiheit)",
    ),
    (
        "(Hund | Informationsfreiheit)",
        "( Hund | (information freiheit) )",
    ),
    ("Verkehrskonzepte", "(verkehrs konzept)"),
    ("Güterverkehr", "(gut verkehr)"),
    # The current decompounder does not split these words correctly, so the decompounding output is ignored.
    ("Verbändebeteiligung", "Verbändebeteiligung"),  # Subtokens: "band", "teil"
    (
        "Informationsfreiheitsgesetzen",
        "Informationsfreiheitsgesetzen",
    ),  # Subtokens: "informations", "freiheits", "setzen"
]


@pytest.mark.elasticsearch
class TestQueryPreprocessor:
    @pytest.mark.parametrize(
        "input_text, expected_output", test_cases, ids=[t[0] for t in test_cases]
    )
    def test_prepare_query(self, input_text, expected_output):
        preprocessor = QueryPreprocessor()

        assert preprocessor.prepare_query(input_text) == expected_output
