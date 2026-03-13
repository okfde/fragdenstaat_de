from django.contrib import messages
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from froide.helper.utils import get_redirect

from .forms import EasylangContactForm


def contact_form_view(request):
    next_url = request.GET.get("next", "")

    if request.method == "POST":
        next_url = request.POST.get("next", next_url)
        form = EasylangContactForm(data=request.POST, request=request)
        if form.is_valid():
            form.send_mail()
            messages.add_message(
                request, messages.SUCCESS, _("We have received your message.")
            )
            return get_redirect(request, default="/")
        else:
            messages.add_message(
                request, messages.ERROR, _("There was a problem with your message.")
            )
    else:
        form = EasylangContactForm(initial={"page_url": next_url})

    return TemplateResponse(
        request,
        "fds_easylang/contact_form_page.html",
        {"form": form, "next": next_url},
    )
