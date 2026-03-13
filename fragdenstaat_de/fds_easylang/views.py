from urllib.parse import urlparse

from django.contrib import messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from fragdenstaat_de.fds_cms.contact import ContactForm


class EasylangContactForm(ContactForm):
    """Contact form without captcha field for accessibility reasons."""

    SPAM_PROTECTION = {"action": "contactform"}


def contact(request):
    if request.method == "POST":
        form = EasylangContactForm(data=request.POST, request=request)
        if form.is_valid():
            form.send_mail()
            messages.add_message(
                request, messages.SUCCESS, "Wir haben Ihre Nachricht erhalten."
            )
        else:
            messages.add_message(
                request, messages.ERROR, "Es gab ein Problem mit Ihrer Nachricht."
            )

        # Redirect back to the page where the form is loaded.
        next_url = urlparse(request.headers.get("referer", "")).path or "/"
        return redirect(next_url)

    form = EasylangContactForm(request=request)

    return TemplateResponse(
        request,
        "fds_cms/feedback.html",
        {"form": form, "form_action": "fds_easylang:contact"},
    )
