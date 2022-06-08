from django.dispatch import Signal

default_app_config = "fragdenstaat_de.fds_newsletter.apps.NewsletterConfig"

subscribed = Signal()  # args: []
unsubscribed = Signal()  # args: []
