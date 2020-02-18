from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _


class FdsDonationConfig(AppConfig):
    name = 'fragdenstaat_de.fds_donation'
    verbose_name = _('FragDenStaat Donations')

    def ready(self):
        # TODO: add export, cancel and merging user hooks
        from payments.signals import status_changed
        from froide_payment.signals import subscription_canceled
        from .listeners import (
            payment_status_changed, subscription_was_canceled
        )

        status_changed.connect(payment_status_changed)
        subscription_canceled.connect(subscription_was_canceled)

        from froide.account.menu import menu_registry, MenuItem

        def get_donation_menu_item(request):
            return MenuItem(
                section='before_settings', order=999,
                url=reverse_lazy('fds_donation:donor-user'),
                label=_('My donations')
            )

        menu_registry.register(get_donation_menu_item)
