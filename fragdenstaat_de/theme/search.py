from elasticsearch_dsl import (
    analyzer, token_filter
)

decomp = token_filter("decomp",
    type='hyphenation_decompounder',
    word_list_path="analysis/dictionary-de.txt",
    hyphenation_patterns_path="analysis/de_DR.xml",
    only_longest_match=True,
    min_subword_size=4
)


def get_text_analyzer():
    return analyzer(
        'fds_analyzer',
        tokenizer='standard',
        filter=[
            'keyword_repeat',
            'lowercase',
            decomp,

            'german_normalization',
            'asciifolding',

            token_filter('de_stemmer', type='stemmer', name='light_german'),
            token_filter('unique_stem', type='unique', only_on_same_position=True)
        ],
    )


def get_search_analyzer():
    return analyzer(
        'fds_search_analyzer',
        tokenizer='standard',
        filter=[
            'keyword_repeat',
            'lowercase',
            decomp,
            token_filter('stop_de', type='stop', stopwords="_german_"),

            'german_normalization',
            'asciifolding',

            token_filter('de_stemmer', type='stemmer', name='light_german'),
            token_filter('unique_stem', type='unique', only_on_same_position=False)
        ],
    )


def get_search_quote_analyzer():
    return analyzer(
        'fds_search_quote_analyzer',
        tokenizer='standard',
        filter=[
            'lowercase',

            'german_normalization',
            'asciifolding',

            token_filter('de_stemmer', type='stemmer', name='light_german'),
        ],
    )
