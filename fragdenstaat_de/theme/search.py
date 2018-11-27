from elasticsearch_dsl import (
    analyzer, token_filter
)


def get_text_analyzer():
    return analyzer(
        'fds_analyzer',
        tokenizer='standard',
        filter=[
            'keyword_repeat',
            token_filter('decomp', type='decompound', subwords_only=True),

            'lowercase',
            token_filter('stop_de', type='stop', stopwords="_german_"),

            'german_normalization',
            'asciifolding',

            token_filter('de_stemmer', type='stemmer', name='light_german'),
            token_filter('unique_stem', type='unique', only_on_same_position=True)
        ],
    )


# def get_search_analyzer():
#     return analyzer(
#         'fds_search_analyzer',
#         tokenizer='standard',
#         filter=[
#             'standard',
#             'lowercase',
#             token_filter('stop_de', type='stop', stopwords="_german_"),
#             'asciifolding',
#             token_filter('de_stemmer', type='stemmer', name='light_german'),
#             token_filter('unique_stem', type='unique', only_on_same_position=True)
#         ],
#     )
