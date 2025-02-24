from django.utils.translation import gettext_lazy as _

from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool


@apphook_pool.register
class FdsEventsApp(CMSApp):
    name = _("Events CMS App")
    app_name = "fds_events"

    def get_urls(self, page=None, language=None, **kwargs):
        return ["fragdenstaat_de.fds_events.urls"]
