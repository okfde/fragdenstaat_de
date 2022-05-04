from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class FdsDonationConfig(AppConfig):
    name = "fragdenstaat_de.fds_donation"
    verbose_name = _("FragDenStaat Donations")

    def ready(self):
        from payments.signals import status_changed

        from froide.account import (
            account_canceled,
            account_email_changed,
            account_merged,
        )
        from froide.account.export import registry

        from froide_payment.signals import sepa_notification, subscription_canceled

        from .listeners import (
            cancel_user,
            export_user_data,
            merge_user,
            payment_status_changed,
            sepa_payment_processing,
            subscription_was_canceled,
            user_email_changed,
        )

        status_changed.connect(payment_status_changed)
        subscription_canceled.connect(subscription_was_canceled)
        sepa_notification.connect(sepa_payment_processing)
        account_canceled.connect(cancel_user)
        account_email_changed.connect(user_email_changed)
        account_merged.connect(merge_user)
        registry.register(export_user_data)

        from froide.account.menu import MenuItem, menu_registry

        def get_donation_menu_item(request):
            return MenuItem(
                section="before_settings",
                order=999,
                url=reverse_lazy("fds_donation:donor-user"),
                label=_("My donations"),
            )

        menu_registry.register(get_donation_menu_item)
