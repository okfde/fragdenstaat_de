import base64
import urllib.parse
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

import qrcode
from fcdocs_annotate.annotation.views import AnnotateDocumentView

from froide.account.models import UserPreference
from froide.foirequest.models import FoiMessage, FoiRequest
from froide.foirequest.views.request_actions import allow_write_foirequest
from froide.frontpage.models import FeaturedRequest
from froide.helper.cache import cache_anonymous_page
from froide.publicbody.models import PublicBody

from .forms import TippspielForm
from .glyphosat import get_glyphosat_document


@cache_anonymous_page(15 * 60)
def index(request):
    successful_foi_requests = FoiRequest.published.successful()[:6]
    featured = (
        FeaturedRequest.objects.all()
        .order_by("-timestamp")
        .select_related("request", "request__public_body")
    )
    return render(
        request,
        "index.html",
        {
            "featured": featured[:3],
            "successful_foi_requests": successful_foi_requests,
            "foicount": FoiRequest.objects.get_send_foi_requests().count(),
            "pbcount": PublicBody.objects.get_list().count(),
        },
    )


@require_POST
@allow_write_foirequest
def glyphosat_download(request, foirequest, message_id):
    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    is_message = (
        message.request.campaign_id == 9
        and message.is_response
        and "Kennwort lautet:" in message.plaintext
    )
    if not is_message:
        messages.add_message(
            request, messages.ERROR, "Leider ist etwas schief gelaufen."
        )
        return redirect(foirequest)

    if not request.POST.get("confirm-notes") == "1":
        messages.add_message(
            request, messages.ERROR, "Sie müssen die Infos zur Kenntnis nehmen!"
        )
        return redirect(foirequest)

    result = get_glyphosat_document(message)
    if result:
        return redirect(result)

    messages.add_message(request, messages.ERROR, "Leider ist etwas schief gelaufen.")
    return redirect(foirequest)


@login_required
def meisterschaften_tippspiel(request):
    error = None
    if request.method == "POST":
        form = TippspielForm(request.POST)
        if form.is_valid():
            form.save(request.user)
        else:
            error = " ".join(" ".join(v) for k, v in form.errors.items())

    prefs = UserPreference.objects.get_preferences(
        request.user, key_prefix="fds_meisterschaften_2020_"
    )

    return JsonResponse({"user": prefs, "error": error})


class FDSAnnotationView(AnnotateDocumentView):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(portal__isnull=True)


@login_required
def scannerapp_postupload(request, message_pk):
    """
    Generate QR code for autologin and redirect to message
    in Scanner app
    """
    autologin_url = request.user.get_autologin_url()
    app_url = f"/app/scanner/deep/message/{message_pk}/"
    next_path = urllib.parse.quote_plus(app_url)
    url = f"{autologin_url}?next={next_path}"
    img = qrcode.make(url, border=2)
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    qrcode_base64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
    data_uri = f"data:image/png;base64,{qrcode_base64}"
    return render(
        request,
        "scannerapp/postupload.html",
        {
            "qrcode": data_uri,
            "app_url": app_url,
        },
    )


def scannerapp_deeplink(request):
    return render(request, "scannerapp/deeplink.html")
