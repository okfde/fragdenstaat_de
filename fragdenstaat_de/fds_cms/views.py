import base64
import urllib.parse
from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

import qrcode
from cms.models import PageContent, PageUrl
from cms.utils import get_current_site
from djangocms_versioning.constants import PUBLISHED
from djangocms_versioning.models import Version
from sekizai.context import SekizaiContext

from froide.helper.search.filters import BaseSearchFilterSet
from froide.helper.search.views import BaseSearchView

from .documents import CMSDocument
from .utils import get_request, render_placeholder


class CMSFilterset(BaseSearchFilterSet):
    query_fields = ["title^5", "description^3", "content"]


class CMSPageSearch(BaseSearchView):
    search_name = "cms"
    template_name = "fds_cms/search.html"
    object_template = "fds_cms/result_item.html"
    model = PageContent
    document = CMSDocument
    filterset = CMSFilterset
    search_url_name = "fds_cms:fds_cms-search"

    def get_base_search(self):
        qs = super().get_base_search()
        url_prefix = self.request.path.rsplit("/", 2)[0] + "/"
        qs = qs.filter("prefix", **{"url.raw": {"value": url_prefix}})
        return qs.filter("term", language=self.request.LANGUAGE_CODE)


def cms_plain_api(request, slug):
    # Create CMS slug path
    base_path = request.current_page.get_absolute_url().rsplit("/", 2)[0]

    if slug == "":
        # Redirect on empty slug
        return redirect(base_path)

    slug_path = "{}/{}".format(base_path[1:], slug)
    site = get_current_site()
    page_url = (
        PageUrl.objects.get_for_site(site)
        .filter(path=slug_path, language=request.LANGUAGE_CODE)
        .select_related("page")
        .first()
    )
    if not page_url:
        raise Http404("Page not found")
    page = page_url.page

    # Find published page content
    page_content = PageContent.objects.filter(
        page=page,
        pk__in=Version.objects.filter(
            content_type=ContentType.objects.get_for_model(PageContent), state=PUBLISHED
        ).values("object_id"),
        language=request.LANGUAGE_CODE,
    ).first()
    if not page_content:
        raise Http404("Page not found")

    content_placeholder = page_content.placeholders.filter(slot="content").first()
    if not content_placeholder:
        raise Http404("Page not found")

    # Use anon request to render the content placeholder
    fake_request = get_request(language=request.LANGUAGE_CODE, path=request.path)
    context = SekizaiContext(fake_request)
    context["request"] = fake_request
    content = render_placeholder(context, content_placeholder, use_cache=True)

    return HttpResponse(content)


@login_required
def scannerapp_postupload(request, message_type, message_pk):
    """
    Generate QR code for autologin and redirect to message
    in Scanner app
    """
    message_type = "draft" if message_type == "draft" else "message"
    app_url = f"{settings.SITE_URL}/app/scanner/deep/{message_type}/{message_pk}/"

    if request.user.can_autologin():
        login_url = request.user.get_autologin_url()
        start_url = urllib.parse.quote_plus(login_url)
        url = f"{app_url}?start_url={start_url}"
    else:
        url = app_url

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


def scannerapp_deeplink(request, slug):
    return render(request, "scannerapp/deeplink.html")
