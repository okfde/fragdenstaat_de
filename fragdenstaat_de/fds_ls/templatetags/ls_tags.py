from django import template

from fragdenstaat_de.fds_cms.contact import ContactForm
from fragdenstaat_de.theme.templatetags.fds_translation_tags import get_languages

register = template.Library()


@register.inclusion_tag("fds_ls/language_toggle.html", takes_context=True)
def language_toggle(context):
    """
    Renders a button to toggle between de and de-ls languages.
    Shows a modal if no translation is available.
    """
    request = context["request"]
    view = context.get("view")
    current_language = request.LANGUAGE_CODE

    # Determine target language
    if current_language == "de-ls":
        target_language = "de"
        button_text = "Leichte Sprache aus"
    else:
        target_language = "de-ls"
        button_text = "Leichte Sprache an"

    # Check if translation exists
    languages = get_languages(request, view)
    language_dict = dict(languages)
    has_target_translation = target_language in language_dict
    target_url = language_dict.get(target_language, "")

    home_url = f"/{target_language}/"

    # Non-CMS pages are currently always handled as not translated.
    is_cms_page = request.current_page

    return {
        "current_language": current_language,
        "target_language": target_language,
        "button_text": button_text,
        "has_translation": has_target_translation and is_cms_page,
        "target_url": target_url,
        "home_url": home_url,
    }


@register.inclusion_tag("fds_ls/feedback.html", takes_context=True)
def render_contact_form(context):
    request = context["request"]

    form_class = ContactForm

    if request.method == "POST":
        form = form_class(request.POST)
    else:
        form = form_class()

    return {"form": form, "request": request}
