from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _


class FdsDonationConfig(AppConfig):
    name = 'fragdenstaat_de.fds_donation'
    verbose_name = _('FragDenStaat Donations')

    def ready(self):
        # TODO: add export, cancel and merging user hooks
        from payments.signals import status_changed
        from .listeners import payment_status_changed

        status_changed.connect(payment_status_changed)

        from froide.account.menu import menu_registry, MenuItem

        def get_donation_menu_item(request):
            return MenuItem(
                section='after_settings', order=0,
                url=reverse_lazy('fds_donation:donor-user'),
                label=_('Your donations')
            )

        menu_registry.register(get_donation_menu_item)
