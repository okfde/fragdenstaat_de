from django.conf import settings
from django.urls import NoReverseMatch

from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from cms.models import Page

from froide.helper.search import search_registry

from .templatetags.fds_cms_tags import get_soft_root


def make_add_search(page_pk):
    def add_search(request):
        page = Page.objects.get(pk=page_pk)
        page_root = get_soft_root(page)
        if not page_root.has_translation(request.LANGUAGE_CODE):
            return
        try:
            return {
                "title": page_root.get_title(request.LANGUAGE_CODE),
                "menu_title": page_root.get_menu_title(request.LANGUAGE_CODE),
                "name": "cms-search-{}".format(page_root.pk),
                "url": page.get_absolute_url(request.LANGUAGE_CODE),
                "order": 7,
            }
        except NoReverseMatch:
            return

    return add_search


@apphook_pool.register
class FdsCmsSearchApp(CMSApp):
    name = "FragDenStaat-CMS-Suche"
    app_name = "fds_cms"

    def get_urls(self, page=None, language=None, **kwargs):
        # FIXME: This is a hack to add a search registry entry
        # for all installed CMS search apps.
        # There doesn't seem to be a 'ready' hook, so we use this.
        if page is not None and language == settings.LANGUAGE_CODE:
            search_registry.register(make_add_search(page.pk))
        return ["fragdenstaat_de.fds_cms.urls"]


@apphook_pool.register
class FdsCmsContactApp(CMSApp):
    name = "FragDenStaat-CMS-Kontakt"
    app_name = "fds_cms_contact"

    def get_urls(self, page=None, language=None, **kwargs):
        return ["fragdenstaat_de.fds_cms.contact"]


@apphook_pool.register
class FdsCmsPlainAPIApp(CMSApp):
    name = "FragDenStaat-CMS-Plain API"
    app_name = "fds_cms_plainapi"

    def get_urls(self, page=None, language=None, **kwargs):
        return ["fragdenstaat_de.fds_cms.urls_plainapi"]


@apphook_pool.register
class DatashowCMSApp(CMSApp):
    name = "Datashow CMS App"
    app_name = "datashow"

    def get_urls(self, page=None, language=None, **kwargs):
        return ["datashow.urls"]


@apphook_pool.register
class ScannerAppDeepLinkCMSApp(CMSApp):
    name = "Scanner App Deep Link CMS App"
    app_name = "scannerapp"

    def get_urls(self, page=None, language=None, **kwargs):
        return ["fragdenstaat_de.fds_cms.urls_scannerapp"]
