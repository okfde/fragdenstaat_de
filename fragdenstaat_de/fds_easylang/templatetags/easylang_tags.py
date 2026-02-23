from django import template

from fragdenstaat_de.fds_cms.contact import ContactForm
from fragdenstaat_de.theme.templatetags.fds_translation_tags import get_languages
from fragdenstaat_de.theme.translation import has_translatable_content

register = template.Library()


@register.inclusion_tag("fds_easylang/easylang_toggle.html", takes_context=True)
def easylang_toggle(context):
    """
    Renders a button to toggle between de and de-ls languages.
    Shows a modal if no translation is available.
    """
    request = context["request"]
    view = context.get("view")
    current_language = request.LANGUAGE_CODE

    # Determine target language.
    target_language = "de-ls" if current_language == "de" else "de"

    # Only look up the target URL when there is actual translated content —
    # non-CMS pages and apphook subpages without per-item translations are
    # excluded because any URL there would be derived from URL manipulation.
    if has_translatable_content(request, view):
        languages = get_languages(request, view)
        language_dict = dict(languages)
        target_url = language_dict.get(target_language, "")
        has_translation = target_language in language_dict
    else:
        target_url = ""
        has_translation = False

    return {
        "current_language": current_language,
        "target_language": target_language,
        "has_translation": has_translation,
        "target_url": target_url,
        "home_url": f"/{target_language}/",
    }


@register.inclusion_tag("fds_easylang/feedback.html", takes_context=True)
def render_contact_form(context):
    request = context["request"]

    form_class = ContactForm

    if request.method == "POST":
        form = form_class(request.POST)
    else:
        form = form_class()

    return {"form": form, "request": request}
