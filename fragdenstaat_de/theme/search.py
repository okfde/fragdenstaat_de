import re

from elasticsearch_dsl import analyzer, token_filter

from froide.helper.search.filters import BaseQueryPreprocessor

# German stop words from Lucene:
# https://github.com/apache/lucene/blob/main/lucene/analysis/common/src/resources/org/apache/lucene/analysis/snowball/german_stop.txt
german_stop = token_filter("german_stop", type="stop", stopwords="_german_")

# Light German stemmer from Lucene.
german_stemmer = token_filter("de_stemmer", type="stemmer", name="light_german")


# Hyphenation decompounder for breaking up German compound words.
# Uses the data from https://github.com/uschindler/german-decompounder.
# Options such as min_subword_size do not seem to work, so short words have been explicitly
# excluded from the word list.
decomp = token_filter(
    "decomp",
    type="hyphenation_decompounder",
    word_list_path="analysis/dictionary-de.txt",
    hyphenation_patterns_path="analysis/de_DR.xml",
    # Prevent "formation" from being detected as a subtoken of "informationsfreiheit".
    no_sub_matches=True,
)


# Analyzer used for preparing the query before sending it to Elasticsearch.
def get_decompounder_analyzer():
    return analyzer(
        "fds_decompounder_analyzer",
        tokenizer="standard",
        filter=[
            "lowercase",
            decomp,
            "german_normalization",
            "asciifolding",
            german_stemmer,
        ],
    )


# Analyzer that is used for indexing text fields.
# Stop words are not excluded, so that the search quote analyzer can find them.
def get_text_analyzer():
    return analyzer(
        "fds_analyzer",
        tokenizer="standard",
        filter=[
            "keyword_repeat",
            "lowercase",
            decomp,
            "german_normalization",
            "asciifolding",
            german_stemmer,
            "remove_duplicates",
        ],
    )


# Analyzer used for analyzing search queries.
# As we preprocess the query with the decompounder analyzer, no decompounding is used here.
def get_search_analyzer():
    return analyzer(
        "fds_search_analyzer",
        tokenizer="standard",
        filter=[
            "keyword_repeat",
            "lowercase",
            german_stop,
            "german_normalization",
            "asciifolding",
            german_stemmer,
            "remove_duplicates",
        ],
    )


# Analyzer for search queries that is used for phrases enclosed in quotes.
# Returns exact matches, therefore only very basic normalization is applied.
def get_search_quote_analyzer():
    return analyzer(
        "fds_search_quote_analyzer",
        tokenizer="standard",
        filter=[
            "keyword_repeat",
            "lowercase",
            "german_normalization",
            "asciifolding",
            "remove_duplicates",
        ],
    )


class QueryPreprocessor(BaseQueryPreprocessor):
    def __init__(self):
        self.analyzer = get_decompounder_analyzer()

    def prepare_query(self, text: str):
        if not self.analyzer:
            return text

        subqueries = self.extract_subqueries(text)

        query_text = ""

        for subquery in subqueries:
            qt = self.get_tokens(subquery)
            query_text += qt + " "

        return query_text

    def extract_subqueries(self, query):
        # Regex to match quoted phrases or individual words.
        pattern = r'("[^"]+")|(\S+)'
        matches = re.findall(pattern, query)
        # Extract matched groups and flatten the list.
        terms = [m[0] if m[0] else m[1] for m in matches]

        return terms

    def get_tokens(self, text):
        if text.startswith('"') and text.endswith('"'):
            return text

        if text.startswith("-"):
            return text

        text = text.replace("-", "")

        if len(text) < 3:
            return text

        response = self.analyzer.simulate(text)
        tokens = [t.token for t in response.tokens]
        print(tokens)

        if len(tokens) < 3:
            return text

        # if tokens[0] == "".join(tokens[1:]):
        return f"{tokens[0]}*"

        # Add a prefix query for the complete word. It allows "Informationsfreiheit"
        # to match in "Informationsfreiheitsgesetz". The second part of the query
        # adds a phrase match for the sub-tokens, so "Informations freiheit" can be matched
        # with "Informations Freiheit" and also with "Informations-Freiheit".
        # return f"({tokens[0]}*) | \"{' '.join(tokens[1:])}\")"

        # Using it with brackets and adding stemming to the decompounder analyzer
        # allows for matches such as "Verkehrskonzept" in "Güterverkehrskonzept"
        # but also leads to unwanted matches such as "Informationen" when searching
        # for "Informationsfreiheit".
        # return f"({tokens[0]}*) | ({' '.join(tokens[1:])}))"
