from django.test import RequestFactory, override_settings
from django.utils.translation import override

import pytest

from fragdenstaat_de.theme.templatetags import fds_translation_tags
from fragdenstaat_de.theme.templatetags.fds_translation_tags import get_languages
from fragdenstaat_de.theme.translation import (
    TranslatedPage,
    TranslatedView,
    get_language_codes,
)

TEST_LANGUAGES = [("de", "German"), ("en", "English"), ("fr", "French")]
TEST_USER_LANGUAGES = [("de", "German"), ("en", "English")]


def _make_request(language: str, path: str = "/some/path/"):
    request = RequestFactory().get(path)
    request.LANGUAGE_CODE = language
    request.current_page = None
    return request


class _FakeTranslatedView(TranslatedView):
    def __init__(self, pages):
        self._pages = pages

    def get_languages(self):
        return self._pages


@pytest.fixture
def stub_translate_url_languages(monkeypatch):
    """Replace translate_url_languages with a URL-resolver-free stub."""

    def _fake(current_url, languages):
        return [TranslatedPage(lang, f"/{lang}{current_url}") for lang in languages]

    monkeypatch.setattr(fds_translation_tags, "translate_url_languages", _fake)


@override_settings(LANGUAGES=TEST_LANGUAGES, USER_LANGUAGES=TEST_USER_LANGUAGES)
@pytest.mark.parametrize(
    "user_only, expected",
    [
        (True, {"de", "en"}),
        (False, {"de", "en", "fr"}),
    ],
)
def test_get_language_codes(user_only, expected):
    assert get_language_codes(user_only=user_only) == expected


@override_settings(LANGUAGES=TEST_LANGUAGES, USER_LANGUAGES=TEST_USER_LANGUAGES)
@pytest.mark.parametrize(
    "user_only, expected_codes",
    [
        (True, {"de", "en"}),
        (False, {"de", "en", "fr"}),
    ],
)
def test_non_cms_page_respects_user_only(
    stub_translate_url_languages, user_only, expected_codes
):
    request = _make_request("de")
    with override("de"):
        result = get_languages(request, view=None, user_only=user_only)

    assert {tp.language_code for tp in result} == expected_codes


@override_settings(LANGUAGES=TEST_LANGUAGES, USER_LANGUAGES=TEST_USER_LANGUAGES)
@pytest.mark.parametrize(
    "user_only, should_include_current",
    [
        (True, False),
        (False, True),
    ],
)
def test_non_cms_current_language_outside_user_languages(
    stub_translate_url_languages, user_only, should_include_current
):
    """When the current request is in a non-user language, user_only=True drops it."""
    request = _make_request("fr")
    with override("fr"):
        result = get_languages(request, view=None, user_only=user_only)

    codes = {tp.language_code for tp in result}

    assert ("fr" in codes) is should_include_current


@override_settings(LANGUAGES=TEST_LANGUAGES, USER_LANGUAGES=TEST_USER_LANGUAGES)
@pytest.mark.parametrize(
    "user_only, expected_codes",
    [
        (True, {"de", "en"}),
        (False, {"de", "en", "fr"}),
    ],
)
def test_translated_view_respects_user_only(user_only, expected_codes):
    request = _make_request("de")
    view = _FakeTranslatedView(
        [
            TranslatedPage("de", "/de/foo/"),
            TranslatedPage("en", "/en/foo/"),
            TranslatedPage("fr", "/fr/foo/"),
        ]
    )
    with override("de"):
        result = get_languages(request, view, user_only=user_only)

    assert {tp.language_code for tp in result} == expected_codes


@override_settings(LANGUAGES=TEST_USER_LANGUAGES, USER_LANGUAGES=TEST_USER_LANGUAGES)
def test_translated_view_does_not_duplicate_current_language():
    request = _make_request("de")
    view = _FakeTranslatedView(
        [
            TranslatedPage("de", "/de/from-view/"),
            TranslatedPage("en", "/en/from-view/"),
        ]
    )
    with override("de"):
        result = get_languages(request, view)

    de_entries = [tp for tp in result if tp.language_code == "de"]

    assert len(de_entries) == 1
    assert de_entries[0].url == "/de/from-view/"


@override_settings(LANGUAGES=TEST_LANGUAGES, USER_LANGUAGES=TEST_LANGUAGES)
def test_languages_sorted_by_name_local():
    """Output is ordered by each language's local name, regardless of input order."""
    request = _make_request("de")
    view = _FakeTranslatedView(
        [
            TranslatedPage("fr", "/fr/foo/"),
            TranslatedPage("en", "/en/foo/"),
            TranslatedPage("de", "/de/foo/"),
        ]
    )
    with override("de"):
        result = get_languages(request, view)

    # name_local: "Deutsch" (de), "English" (en), "français" (fr)
    assert [tp.language_code for tp in result] == ["de", "en", "fr"]
