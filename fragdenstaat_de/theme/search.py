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


# Token filter that runs multiple filters in parallel and merges the results.
# Un-stemmed subwords from the decompounder are discarded while the original
# tokens (including full compound words) are included in the output which allows
# for exact matches.
multiplexer = token_filter(
    "multiplexer",
    type="multiplexer",
    filters=[
        # Apply normalization and stemming to full words.
        ["german_normalization", "asciifolding", german_stemmer],
        # Apply decompounding and process the resulting subwords.
        [
            decomp,
            "german_normalization",
            "asciifolding",
            german_stemmer,
        ],
    ],
)


def get_text_analyzer():
    """
    Return an analyzer that is used for indexing text fields.

    Stop words are not excluded, so that the search quote analyzer can find them.
    """
    return analyzer(
        "fds_analyzer",
        tokenizer="standard",
        filter=[
            "lowercase",
            multiplexer,
        ],
    )


def get_search_analyzer():
    """
    Return an analyzer used for analyzing search queries.

    As the query is preprocessed with the decompounder analyzer, no decompounding is done here.
    """
    return analyzer(
        "fds_search_analyzer",
        tokenizer="standard",
        filter=[
            "lowercase",
            german_stop,
            "german_normalization",
            "asciifolding",
            german_stemmer,
        ],
    )


def get_search_quote_analyzer():
    """
    Return a search query analyzer that is used for phrases enclosed in quotes.

    This analyzer is expected to return exact matches, therefore only very basic
    normalization is applied.
    """
    return analyzer(
        "fds_search_quote_analyzer",
        tokenizer="standard",
        filter=[
            "lowercase",
        ],
    )


def get_decompounder_analyzer():
    """
    Return an analyzer that decompounds compound words.

    Used for preparing the query before sending it to Elasticsearch.
    """
    return analyzer(
        "fds_decompounder_analyzer",
        tokenizer="standard",
        filter=[
            "lowercase",
            decomp,
        ],
    )


def get_stemming_analyzer():
    """
    Return an analyzer that applies stemming to the tokens.

    Used for preparing the query before sending it to Elasticsearch.
    """
    return analyzer(
        "fds_stemming_analyzer",
        tokenizer="standard",
        filter=[
            "german_normalization",
            "asciifolding",
            german_stemmer,
        ],
    )


class QueryPreprocessor(BaseQueryPreprocessor):
    """
    Preprocess the search query to improve search results.

    Specifically, compound words are handled so that
    - subtokens retrieved from the decompounder are connected with AND instead of OR,
    - the subtokens are stemmed to match different word forms,
    - this preprocessing is only applied if the subtokens actually form the original
      word.

    Some background can be found in this article:
    https://www.elastic.co/search-labs/blog/compound-word-search

    According to this article, tokens from a decompounder token filter are by default
    connected with OR. In order to avoid certain unexpected matches, it is proposed to
    preprocess the query so that the subwords are connected with AND instead.

    This is the approach taken here, however, the results are still not ideal. Searching
    for "Informationsfreiheit" still matches documents containing the words "Information"
    and "Freiheit" in different parts of the text. This is to some extent intended as it
    allows for semantically related matches such as "Freiheit der Information" but can
    also lead to unexpected and confusing results.

    Phrase matches ("information freiheit") to ensure that the subtokens appear in the
    correct order next to each other are not easily possible because all the subtokens
    are assigned the same position by the decompounder filter (see also this issue:
    https://github.com/apache/lucene/issues/14624).

    Still, the user has the option to get exact matches for compound words by enclosing
    the search term in quotes ("Informationsfreiheit").
    """

    def __init__(self):
        self.decompounder = get_decompounder_analyzer()
        self.stemmer = get_stemming_analyzer()

    def prepare_query(self, text: str):
        subqueries = [self.get_subquery(query) for query in self.split_query(text)]

        return " ".join(subqueries).strip()

    def split_query(self, query):
        # Regex to match
        # - quoted phrases with an optional slop (e.g. ~1)
        # - individual words
        # - parentheses
        pattern = r'("[^"]+"(~\d+)?)|([^\s()]+)|([()])'
        matches = re.findall(pattern, query)

        # Extract matched groups and flatten the list.
        return [m[0] or m[2] or m[3] for m in matches if m[0] or m[2] or m[3]]

    def get_subquery(self, text):
        # Ignore words with special query syntax.
        if self.has_special_syntax(text):
            return text

        # Decompound the text.
        tokens = self.decompound(text)

        # The first token is always the full word.
        # In addition, there should be at least two subtokens to build a meaningful query.
        if len(tokens) < 3:
            return text

        # Concatenation of the subtokens should yield the original word.
        # Use `startswith` because the decompounder sometimes removes the last character,
        # e.g. "gesetze" -> "gesetz".
        if not tokens[0].startswith("".join(tokens[1:])):
            return text

        # Stem the tokens to match different word forms.
        stemmed_tokens = self.stem(tokens)

        # Create a query in which the subtokens are (implicitly) connected with AND.
        # Use parentheses to group the tokens together.
        return f"({' '.join(stemmed_tokens[1:])})"

    def has_special_syntax(self, text):
        """
        Return True if the text contains special query syntax that should not be modified.

        Specifically, this includes:
        - Negation with a leading "-"
        - Exact phrases enclosed in quotes
        - Fuzzy search/slop specification with a trailing "~" and a number

        For details, see the Elasticsearch documentation:
        https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-simple-query-string-query#simple-query-string-query-notes
        """
        if text.startswith("-"):
            return True

        if text.startswith('"') and text.endswith('"'):
            return True

        if re.match(r".+~\d+$", text):
            return True

        return False

    def decompound(self, text):
        response = self.decompounder.simulate(text)
        tokens = [t.token for t in response.tokens]

        return tokens

    def stem(self, tokens):
        text = " ".join(tokens)

        response = self.stemmer.simulate(text)
        tokens = [t.token for t in response.tokens]

        return tokens
