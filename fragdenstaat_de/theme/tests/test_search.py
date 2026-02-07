import pytest
from django_elasticsearch_dsl.fields import TextField

from froide.helper.search import (
    get_ngram_analyzer,
    get_search_analyzer,
    get_search_quote_analyzer,
    get_text_analyzer,
)

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

ANALYZERS = {
    "analyzer": get_text_analyzer(),
    "search_analyzer": get_search_analyzer(),
    "search_quote_analyzer": get_search_quote_analyzer(),
}


def get_document_classes():
    from froide_evidencecollection.documents import EvidenceDocument, PersonDocument

    from froide.foirequest.documents import FoiRequestDocument
    from froide.publicbody.documents import PublicBodyDocument

    from fragdenstaat_de.fds_blog.documents import ArticleDocument
    from fragdenstaat_de.fds_cms.documents import CMSDocument

    return [
        ArticleDocument,
        CMSDocument,
        FoiRequestDocument,
        PublicBodyDocument,
        EvidenceDocument,
        PersonDocument,
    ]


def get_text_fields(document_class):
    return {
        field_name: field
        for field_name, field in document_class._fields.items()
        if isinstance(field, TextField)
    }


class TestDocumentAnalyzerConfiguration:
    # Text fields that are not intended for full-text search.
    NON_FTS_FIELDS = ["author", "first_name", "last_name", "url"]

    @pytest.mark.parametrize(
        "document_class", get_document_classes(), ids=lambda doc: doc.__name__
    )
    def test_text_fields_have_correct_analyzers(self, document_class):
        """Test that all text fields in the document have the correct analyzers configured."""
        text_fields = get_text_fields(document_class)

        for field_name, field in text_fields.items():
            if field_name == "name_auto":
                self._assert_ngram_field(field_name, field)
            elif field_name in self.NON_FTS_FIELDS:
                self._assert_no_analyzers(field_name, field)
            else:
                self._assert_full_text_analyzers(field_name, field)

    def _assert_ngram_field(self, field_name, field):
        """Test that the field is configured to use the ngram analyzer."""
        assert field.analyzer == get_ngram_analyzer(), (
            f"Field '{field_name}' should use ngram analyzer"
        )
        # If no separate search analyzer is set, field.analyzer is used for searching.
        assert hasattr(field, "search_analyzer") is False, (
            f"Field '{field_name}' should not have 'search_analyzer' set"
        )
        assert hasattr(field, "search_quote_analyzer") is False, (
            f"Field '{field_name}' should not have 'search_quote_analyzer' set"
        )

    def _assert_no_analyzers(self, field_name, field):
        """Test that the field has no analyzers set, i.e. uses the standard analyzer."""
        for analyzer_type in ANALYZERS.keys():
            analyzer = getattr(field, analyzer_type, None)
            assert analyzer is None, (
                f"Field '{field_name}' should not have '{analyzer_type}' set"
            )

    def _assert_full_text_analyzers(self, field_name, field):
        """Test that the field has the correct full-text analyzers set."""
        for analyzer_type, expected_analyzer in ANALYZERS.items():
            actual_analyzer = getattr(field, analyzer_type, None)
            actual_name = actual_analyzer._name if actual_analyzer else None

            assert actual_name == expected_analyzer._name, (
                f"Field '{field_name}' has incorrect {analyzer_type}: "
                f"{actual_name} != {expected_analyzer._name}"
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
