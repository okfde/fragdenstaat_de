from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool


@apphook_pool.register
class FdsCmsSearchApp(CMSApp):
    name = 'FragDenStaat-CMS-Suche'
    app_name = 'fds_cms'

    def get_urls(self, page=None, language=None, **kwargs):
        return ['fragdenstaat_de.fds_cms.urls']
