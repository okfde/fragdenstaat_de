from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool


@apphook_pool.register
class EasylangContactApp(CMSApp):
    name = "Leichte Sprache Kontakt"
    app_name = "fds_easylang"

    def get_urls(self, page=None, language=None, **kwargs):
        return ["fragdenstaat_de.fds_easylang.urls"]
