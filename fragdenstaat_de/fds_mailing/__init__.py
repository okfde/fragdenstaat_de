from typing import Any, Callable, NamedTuple

from django.dispatch import Signal
from django.http import HttpRequest

default_app_config = "fragdenstaat_de.fds_mailing.apps.FdsMailingConfig"

mailing_submitted = Signal()  # args: []
gather_mailing_preview_context = Signal()


class MailingPreviewContextProvider(NamedTuple):
    name: str
    options: dict[str, str]
    provide_context: Callable[[str, HttpRequest], dict[str, Any]]
