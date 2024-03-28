import re
import signal
import subprocess
from collections import namedtuple

from django.urls import reverse

import payments.core
import pytest
import stripe
from playwright.sync_api import Page

import froide_payment.provider.stripe

WebhookEvent = namedtuple("WebhookEvent", ["timestamp", "name", "event_id"])

STRIPE_TEST_IBANS = {
    "success": "DE89370400440532013000",
    "failed": "DE62370400440532013001",
    "disputed": "DE35370400440532013002",
}


class StripeWebhookForwarder:
    WH_EVENT_RE = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+-->\s+([\w\.]+)\s+\[(\w+)\]"
    )

    def __init__(self, secret_key: str, forward_url: str, final_event):
        self.secret_key = secret_key
        self.forward_url = forward_url.replace("http://", "")
        self.webhooks_called = None
        self.final_event = final_event

    def get_webhook_secret(self):
        webhook_secret = subprocess.run(
            ["stripe", "listen", "--api-key", self.secret_key, "--print-secret"],
            stdout=subprocess.PIPE,
            check=True,
            universal_newlines=True,
        ).stdout.strip()
        assert re.match(r"^whsec_\w{32,}$", webhook_secret), webhook_secret
        return webhook_secret

    def __enter__(self):
        process_args = [
            "stripe",
            "listen",
            "--api-key",
            self.secret_key,
            "--forward-to",
            self.forward_url,
        ]
        self.proc = subprocess.Popen(
            process_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.webhooks_called = []
        try:
            if self.proc.returncode is None:
                for line in self.proc.stdout:
                    events = self.make_webhook_events(line)
                    if not events:
                        continue
                    self.webhooks_called.extend(events)
                    if any([ev.name == self.final_event for ev in events]):
                        break
                self.proc.send_signal(signal.SIGINT)
                try:
                    returncode = self.proc.wait(1)
                except subprocess.TimeoutExpired:
                    pass
                else:
                    if returncode != 0:
                        raise Exception("Error stopping stripe webhook forwarder")
            elif exc_val is not None:
                self.proc.send_signal(signal.SIGKILL)
        finally:
            if self.proc.returncode is None:
                self.proc.send_signal(signal.SIGKILL)

    def make_webhook_events(self, log: str):
        return [WebhookEvent(*m.groups()) for m in self.WH_EVENT_RE.finditer(log)]


@pytest.mark.django_db
def test_recurring_sepa_donation(page: Page, live_server, settings, monkeypatch):
    settings.SITE_URL = live_server.url
    # PAYMENT_HOST setting is copied to module level on import, need to patch it
    monkeypatch.setattr(
        payments.core, "PAYMENT_HOST", live_server.url.replace("http://", "")
    )
    # Disable confirmation checks for testing
    monkeypatch.setattr(
        froide_payment.provider.stripe, "requires_confirmation", lambda r, p, d: False
    )
    stripe.api_key = settings.PAYMENT_VARIANTS["sepa"][1]["secret_key"]

    page.goto(live_server.url + reverse("fds_donation:donate"))
    page.get_by_role("button", name="5 Euro").click()
    page.get_by_text("monatlich").click()
    page.get_by_placeholder("Vorname").click()
    page.get_by_placeholder("Vorname").fill("Peter")
    page.get_by_placeholder("Nachname").fill("Parker")
    donor_email = "peter.parker@example.com"
    page.get_by_placeholder("z.B. name@beispiel.de").fill(donor_email)
    page.get_by_text("SEPA-Lastschrift", exact=True).click()
    page.get_by_text("Nein, danke.").nth(1).click()
    page.get_by_text("Nein, danke.").nth(2).click()
    page.get_by_label("Was ist drei plus vier?").fill("7")
    page.get_by_role("button", name="Jetzt spenden").click()
    page.get_by_placeholder("z.B. DE12...").click()
    page.get_by_placeholder("z.B. DE12...").fill(STRIPE_TEST_IBANS["success"])

    webhook_url = live_server.url + "/payments/process/sepa/"
    secret_key = settings.PAYMENT_VARIANTS["sepa"][1]["secret_key"]
    assert secret_key.startswith("sk_test_")

    forwarder = StripeWebhookForwarder(
        secret_key, webhook_url, final_event="invoice.payment_succeeded"
    )
    settings.PAYMENT_VARIANTS["sepa"][1][
        "signing_secret"
    ] = forwarder.get_webhook_secret()
    with forwarder:
        page.get_by_role("button", name="Jetzt spenden").click()
        page.wait_for_url("**spenden/spende/spenden/abgeschlossen/**")
        assert page.get_by_text("Vielen Dank für Ihre Spende!").is_visible()
        assert page.get_by_text(donor_email).is_visible()

        print("waiting for webhooks to complete...")

    print(forwarder.webhooks_called)
    webhooks = [webhook.name for webhook in forwarder.webhooks_called]
    print(webhooks)

    # stripe_event_id = [
    #     event.event_id
    #     for event in forwarder.webhooks_called
    #     if event.name == "invoice.payment_succeeded"
    # ][0]
    # event = stripe.Event.retrieve(stripe_event_id)
