from typing import Sequence

from django import template
from django.http import HttpRequest
from django.urls import translate_url
from django.utils.translation import get_language_info

from fragdenstaat_de.theme.translation import (
    TranslatedPage,
    TranslatedView,
    get_other_languages,
)

register = template.Library()


def _translate_url_languages(current_url: str, languages) -> list[TranslatedPage]:
    """Build translated page list via Django's translate_url()."""
    result = []
    for language in languages:
        url = translate_url(current_url, language)
        if url != current_url:
            result.append(TranslatedPage(language, url))
    return result


@register.simple_tag
def get_languages(request: HttpRequest, view) -> Sequence[TranslatedPage]:
    current_language = request.LANGUAGE_CODE
    other_languages = get_other_languages()

    current_url = request.get_full_path()

    page = getattr(request, "current_page", None) or None

    if isinstance(view, TranslatedView):
        languages = view.get_languages()
    elif page and not page.get_application_urls():
        # Plain CMS page: use actual published page URLs.
        urls = page.get_urls()
        languages = [
            TranslatedPage(url.language, url.get_absolute_url(url.language))
            for url in urls
        ]
    elif page:
        # CMS apphook page: only include languages for which the CMS page
        # itself has published content, otherwise the language prefix URL
        # would trigger CMS's redirect_on_fallback.
        published_languages = set(
            page.pagecontent_set.values_list("language", flat=True)
        )
        languages = _translate_url_languages(
            current_url,
            (lang for lang in other_languages if lang in published_languages),
        )
    else:
        # Non-CMS page.
        languages = _translate_url_languages(current_url, other_languages)

    # add current language, if omitted
    if current_language not in dict(languages).keys():
        languages = list(languages)
        languages += [TranslatedPage(request.LANGUAGE_CODE, current_url)]

    return sorted(languages, key=lambda page: get_language_info(page[0])["name_local"])
