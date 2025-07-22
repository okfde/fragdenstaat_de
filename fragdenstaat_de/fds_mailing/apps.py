from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FdsMailingNoConfig(AppConfig):
    name = "fragdenstaat_de.fds_mailing"
    verbose_name = _("FragDenStaat Mailings")


class FdsMailingConfig(AppConfig):
    name = "fragdenstaat_de.fds_mailing"
    verbose_name = _("FragDenStaat Mailings")
    default = True

    def ready(self):
        from froide.bounce.signals import email_bounced
        from froide.helper.email_sending import mail_middleware_registry

        from . import (
            actions,  # noqa: F401
            preview,  # noqa: F401
        )
        from .middleware import EmailTemplateMiddleware
        from .utils import handle_bounce

        mail_middleware_registry.register(EmailTemplateMiddleware())
        email_bounced.connect(handle_bounce)
