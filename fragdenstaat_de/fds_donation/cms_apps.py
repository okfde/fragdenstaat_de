from django.utils.translation import gettext_lazy as _

from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool


@apphook_pool.register
class FdsDonationApp(CMSApp):
    name = _("FragDenStaat Donation Gift App")
    app_name = "fds_donation"

    def get_urls(self, page=None, language=None, **kwargs):
        return ["fragdenstaat_de.fds_donation.urls"]
