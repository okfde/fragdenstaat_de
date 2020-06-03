from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class FdsDonationConfig(AppConfig):
    name = 'fragdenstaat_de.fds_donation'
    verbose_name = _('FragDenStaat Donations')

    def ready(self):
        from payments.signals import status_changed
        from froide.account import (
            account_canceled, account_merged
        )
        from froide.account.export import registry
        from froide_payment.signals import subscription_canceled
        from .listeners import (
            payment_status_changed, subscription_was_canceled,
            cancel_user, merge_user, export_user_data
        )

        status_changed.connect(payment_status_changed)
        subscription_canceled.connect(subscription_was_canceled)
        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)
        registry.register(export_user_data)

        from froide.account.menu import menu_registry, MenuItem

        def get_donation_menu_item(request):
            return MenuItem(
                section='before_settings', order=999,
                url=reverse_lazy('fds_donation:donor-user'),
                label=_('My donations')
            )

        menu_registry.register(get_donation_menu_item)
