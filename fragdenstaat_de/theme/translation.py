from typing import NamedTuple, Sequence

from django.conf import settings
from django.utils.translation import get_language

LANGUAGE_CODES = set(dict(settings.LANGUAGES).keys())


def get_other_languages() -> set[str]:
    """
    returns the language codes of all settings.LANGUAGES,
    except for the language code of the current request.
    """
    other_languages = LANGUAGE_CODES.copy()
    other_languages.remove(get_language())
    return other_languages


class TranslatedPage(NamedTuple):
    language_code: str
    url: str


class TranslatedView:
    """
    Intended for views that do not use django-native i18n urls (i.e. fds_blog articles).
    Picked up by the language switcher element via the get_languages template tag.
    """

    def get_languages(self) -> Sequence[TranslatedPage]:
        """
        Returns a mapping of all translations of this page.
        The current language may be omitted.
        """
        raise NotImplementedError
