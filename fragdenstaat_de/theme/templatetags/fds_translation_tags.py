from typing import Sequence

from django import template
from django.conf import settings
from django.urls import translate_url
from django.utils.translation import get_language_info

from fragdenstaat_de.theme.translation import TranslatedPage, TranslatedView

register = template.Library()


@register.simple_tag
def get_languages(request, view) -> Sequence[TranslatedPage]:
    if isinstance(view, TranslatedView):
        languages = view.get_languages()
    elif hasattr(request, "current_page") and request.current_page:
        page = request.current_page
        urls = page.get_urls()

        languages = [
            TranslatedPage(url.language, url.get_absolute_url(url.language))
            for url in urls
        ]
    else:
        languages = [
            TranslatedPage(language, translate_url(request.get_full_path(), language))
            for language, _ in settings.LANGUAGES
        ]

    return sorted(languages, key=lambda page: get_language_info(page[0])["name_local"])
