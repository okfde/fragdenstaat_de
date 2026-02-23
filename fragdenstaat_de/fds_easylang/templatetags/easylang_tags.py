from django import template

from fragdenstaat_de.fds_cms.contact import ContactForm
from fragdenstaat_de.theme.templatetags.fds_translation_tags import get_languages

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

    # Check if translation exists.
    languages = get_languages(request, view)
    language_dict = dict(languages)
    target_url = language_dict.get(target_language, "")

    # For non-CMS pages, get_languages() generates URLs via translate_url()
    # which always succeeds. Those URLs would just be redirected back by the
    # middleware, so only treat CMS pages as having a real translation.
    page = getattr(request, "current_page", None) or None
    has_translation = target_language in language_dict and page is not None

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
