from elasticsearch_dsl import analyzer, token_filter

decomp = token_filter(
    "decomp",
    type="hyphenation_decompounder",
    word_list_path="analysis/dictionary-de.txt",
    hyphenation_patterns_path="analysis/de_DR.xml",
    only_longest_match=True,
    min_subword_size=4,
)


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
            token_filter("de_stemmer", type="stemmer", name="light_german"),
            "remove_duplicates",
        ],
    )


def get_search_analyzer():
    return get_text_analyzer()


def get_search_quote_analyzer():
    return analyzer(
        "fds_search_quote_analyzer",
        tokenizer="standard",
        filter=[
            "keyword_repeat",
            "lowercase",
            "german_normalization",
            "asciifolding",
            token_filter("de_stemmer", type="stemmer", name="light_german"),
            "remove_duplicates",
        ],
    )
