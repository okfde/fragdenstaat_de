from typing import Sequence

from django import template
from django.http import HttpRequest
from django.utils.translation import get_language_info

from fragdenstaat_de.theme.translation import (
    TranslatedPage,
    TranslatedView,
    get_other_languages,
    get_published_languages,
    get_published_page_urls,
    translate_apphook_subpage,
    translate_url_languages,
)

register = template.Library()


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
        languages = get_published_page_urls(page)
    elif page:
        # CMS apphook page: check if we're on the apphook root or a subpage.
        page_url = page.get_absolute_url(current_language)
        is_apphook_root = current_url.rstrip("/") == (page_url or "").rstrip("/")

        if is_apphook_root:
            # On the apphook root CMS page itself: only include languages for
            # which the CMS page has published content, otherwise the language
            # prefix URL would trigger CMS's redirect_on_fallback.
            published_languages = get_published_languages(page)
            languages = translate_url_languages(
                current_url,
                (lang for lang in other_languages if lang in published_languages),
            )
        else:
            # On a subpage served by the app's URL patterns.
            # translate_url fails here because CMS's AppRegexURLResolver
            # only returns patterns for the active language.
            languages = translate_apphook_subpage(
                request, page, current_language, other_languages
            )
    else:
        # Non-CMS page.
        languages = translate_url_languages(current_url, other_languages)

    # add current language, if omitted
    if current_language not in dict(languages).keys():
        languages = list(languages)
        languages += [TranslatedPage(current_language, current_url)]

    return sorted(languages, key=lambda page: get_language_info(page[0])["name_local"])
