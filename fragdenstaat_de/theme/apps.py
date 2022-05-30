from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ThemeConfig(AppConfig):
    name = "fragdenstaat_de.theme"
    verbose_name = _("FragDenStaat")

    def ready(self):
        from froide.account import account_future_canceled
        from froide.account.forms import user_extra_registry

        from .forms import SignupUserCheckExtra

        user_extra_registry.register("registration", SignupUserCheckExtra())
        account_future_canceled.connect(start_legal_backup)


def start_legal_backup(sender, **kwargs):
    from .tasks import make_legal_backup

    make_legal_backup.delay(sender.id)
