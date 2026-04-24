from typing import NamedTuple, Sequence

from django.urls import NoReverseMatch, Resolver404, resolve, reverse, translate_url
from django.utils.translation import override

from cms.apphook_pool import apphook_pool

from froide.helper.language import get_language_choices, get_user_language_choices


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


def get_language_codes(user_only: bool = True) -> set[str]:
    """
    Returns the set of language codes available for language switching.

    When user_only is True (default), uses settings.USER_LANGUAGES
    (the subset of languages surfaced to end users). Otherwise uses
    the full settings.LANGUAGES.
    """
    choices = get_user_language_choices() if user_only else get_language_choices()
    return set(dict(choices).keys())


def get_published_languages(page) -> list[str]:
    """Return the language codes for which a CMS page has published content."""
    return page.get_languages(admin_manager=False)


def get_published_page_urls(page) -> list[TranslatedPage]:
    """Return TranslatedPage entries for each published language of a plain CMS page."""
    published_languages = get_published_languages(page)
    return [
        TranslatedPage(url.language, url.get_absolute_url(url.language))
        for url in page.get_urls()
        if url.language in published_languages
    ]


def translate_url_languages(current_url: str, languages) -> list[TranslatedPage]:
    """Build translated page list via Django's translate_url()."""
    result = []
    for language in languages:
        url = translate_url(current_url, language)
        if url != current_url:
            result.append(TranslatedPage(language, url))
    return result


def get_apphook_urlconf(page, language: str) -> str | None:
    """Return the URL module path for a CMS page's apphook, or None."""
    apphook_name = page.get_application_urls()
    apphook = apphook_pool.get_apphook(apphook_name)
    if not apphook:
        return None
    return apphook.get_urls(page=page, language=language)[0]


def translate_apphook_url(
    page, match, url_module: str, language: str, query_string: str = ""
) -> TranslatedPage | None:
    """Translate a resolved apphook URL match to a single target language.

    Combines the CMS page URL in the target language with the app path
    reversed in the target language, bypassing CMS's resolver.
    """
    page_url = page.get_absolute_url(language)
    if not page_url:
        return None

    with override(language):
        try:
            app_path = reverse(
                match.url_name,
                args=match.args,
                kwargs=match.kwargs,
                urlconf=url_module,
            )
        except NoReverseMatch:
            return None

    translated_url = page_url.rstrip("/") + app_path
    if query_string:
        translated_url += "?" + query_string

    return TranslatedPage(language, translated_url)


def translate_apphook_subpage(
    request, page, current_language: str, target_languages
) -> list[TranslatedPage]:
    """Translate a CMS apphook subpage URL to other languages.

    translate_url() fails for apphook subpages because CMS's
    AppRegexURLResolver only returns patterns for the active language,
    so reverse() under override(target_lang) cannot find the pattern.

    This bypasses CMS by resolving and reversing directly against the
    apphook's own URL module, then combining with the CMS page URL in
    the target language (which handles translated slugs and the language
    prefix via i18n_patterns).
    """
    page_url = page.get_absolute_url(current_language)
    if not page_url:
        return []

    url_module = get_apphook_urlconf(page, current_language)
    if not url_module:
        return []

    app_subpath = request.path[len(page_url.rstrip("/")) :]
    try:
        match = resolve(app_subpath, urlconf=url_module)
    except Resolver404:
        return []

    query_string = request.META.get("QUERY_STRING", "")

    return [
        translated
        for lang in target_languages
        if (
            translated := translate_apphook_url(
                page, match, url_module, lang, query_string
            )
        )
    ]
