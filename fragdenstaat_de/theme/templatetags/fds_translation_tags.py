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


@register.simple_tag
def get_languages(request: HttpRequest, view) -> Sequence[TranslatedPage]:
    current_language = request.LANGUAGE_CODE
    other_languages = get_other_languages()

    current_url = request.get_full_path()

    if isinstance(view, TranslatedView):
        languages = view.get_languages()
    elif (
        hasattr(request, "current_page")
        and request.current_page
        and not request.current_page.get_application_urls()
    ):
        page = request.current_page

        urls = page.get_urls()

        languages = [
            TranslatedPage(url.language, url.get_absolute_url(url.language))
            for url in urls
        ]
    else:
        languages = []
        for language in other_languages:
            url = translate_url(current_url, language)
            if url != current_url:
                languages.append(TranslatedPage(language, url))

    # add current language, if omitted
    if current_language not in dict(languages).keys():
        languages = list(languages)
        languages += [TranslatedPage(request.LANGUAGE_CODE, current_url)]

    return sorted(languages, key=lambda page: get_language_info(page[0])["name_local"])
