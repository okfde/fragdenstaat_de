from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FdsMailingConfig(AppConfig):
    name = 'fragdenstaat_de.fds_mailing'
    verbose_name = _('FragDenStaat Mailings')

    def ready(self):
        from froide.helper.email_sending import mail_middleware_registry

        from .middleware import EmailTemplateMiddleware

        mail_middleware_registry.register(EmailTemplateMiddleware())
