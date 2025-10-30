from typing import NamedTuple, Sequence


class TranslatedPage(NamedTuple):
    language_code: str
    url: str


class TranslatedView:
    """
    Intended for views that do not use django-native i18n urls (i.e. fds_blog articles).
    Picked up by the language switcher element via the get_languages template tag.
    """

    def get_languages(self) -> Sequence[TranslatedPage]:
        """returns a mapping of all translations of this page"""
        raise NotImplementedError
