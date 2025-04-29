from django.dispatch import Signal

default_app_config = "fragdenstaat_de.fds_mailing.apps.FdsMailingConfig"

mailing_submitted = Signal()  # args: []
