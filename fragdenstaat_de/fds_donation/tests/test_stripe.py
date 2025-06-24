import re
import subprocess
import time
from collections import namedtuple
from datetime import datetime
from decimal import Decimal

from django.core import mail
from django.urls import reverse

import froide_payment.provider.stripe
import payments.core
import pytest
import stripe
from playwright.sync_api import Page

from fragdenstaat_de.fds_donation.models import Donation

from .utils import ProcessReader

WebhookEvent = namedtuple("WebhookEvent", ["timestamp", "name", "event_id"])

STRIPE_TEST_IBANS = {
    "success": "DE89370400440532013000",
    "failed": "DE62370400440532013001",
    "disputed": "DE35370400440532013002",
    "additional_fields": "CH9300762011623852957",
}
STRIPE_TEST_CARDS = {
    "success": "4242424242424242",
    "declined": "4000000000000002",
}


class StripeWebhookForwarder:
    WH_EVENT_RE = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+-->\s+([\w\.]+)\s+\[(\w+)\]"
    )

    def __init__(self, secret_key: str, forward_url: str):
        self.secret_key = secret_key
        self.forward_url = forward_url.replace("http://", "")
        self.webhooks_called = None
        self.final_event = None
        self.final_event_max = 1

    def get_webhook_secret(self):
        webhook_secret = subprocess.run(
            ["stripe", "listen", "--api-key", self.secret_key, "--print-secret"],
            stdout=subprocess.PIPE,
            check=True,
            universal_newlines=True,
        ).stdout.strip()
        assert re.match(r"^whsec_\w{32,}$", webhook_secret), webhook_secret
        return webhook_secret

    def set_final_event(self, final_event: str, final_event_max: int = 1):
        self.final_event = final_event
        self.final_event_max = final_event_max

    def __enter__(self):
        process_args = [
            "stripe",
            "listen",
            "--api-key",
            self.secret_key,
            "--forward-to",
            self.forward_url,
            "--color",
            "off",
        ]
        self.proc = ProcessReader(process_args)
        self.proc.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.webhooks_called = []
        final_event_count = 0
        found_final_event = False
        if exc_val is not None:
            self.proc.stop()
            return
        try:
            while True:
                line = self.proc.readline()
                if found_final_event:
                    if "] POST" in line:
                        break
                else:
                    events = self.make_webhook_events(line)
                    if not events:
                        continue
                self.webhooks_called.extend(events)
                final_event_count += len(
                    [ev for ev in events if ev.name == self.final_event]
                )
                if final_event_count >= self.final_event_max:
                    found_final_event = True
        finally:
            self.proc.stop()

    def make_webhook_events(self, log: str):
        return [WebhookEvent(*m.groups()) for m in self.WH_EVENT_RE.finditer(log)]


@pytest.fixture(autouse=True)
def skip_stripe_if_no_key(request, settings):
    if request.node.get_closest_marker("stripe"):
        secret_key = settings.PAYMENT_VARIANTS["sepa"][1]["secret_key"]
        if not secret_key:
            pytest.skip("skipped stripe test because stripe key is not set")


@pytest.fixture
def stripe_sepa_setup(settings, live_server, monkeypatch):
    settings.SITE_URL = live_server.url
    # PAYMENT_HOST setting is copied to module level on import, need to patch it
    monkeypatch.setattr(
        payments.core, "PAYMENT_HOST", live_server.url.replace("http://", "")
    )
    # Disable confirmation checks for testing
    monkeypatch.setattr(
        froide_payment.provider.stripe, "requires_confirmation", lambda r, p, d: False
    )

    secret_key = settings.PAYMENT_VARIANTS["sepa"][1]["secret_key"]
    assert secret_key.startswith("sk_test_")
    stripe.api_key = secret_key

    webhook_url = live_server.url + "/payments/process/sepa/"
    forwarder = StripeWebhookForwarder(secret_key, webhook_url)
    settings.PAYMENT_VARIANTS["sepa"][1]["signing_secret"] = (
        forwarder.get_webhook_secret()
    )
    yield forwarder


def fill_donation_page(page: Page, donor_email):
    page.get_by_placeholder("Vorname").fill("Peter")
    page.get_by_placeholder("Nachname").fill("Parker")
    page.get_by_placeholder("z.B. name@beispiel.de").fill(donor_email)
    page.get_by_text("Nein, danke.").nth(1).click()
    page.get_by_text("Nein, danke.").nth(2).click()
    page.get_by_label("Was ist drei plus vier?").fill("7")


DONATION_DONE_URL = re.compile(r".*spenden/spende/spenden/abgeschlossen/.*")


@pytest.mark.django_db
@pytest.mark.stripe
def test_sepa_recurring_donation_success(page: Page, live_server, stripe_sepa_setup):
    donor_email = "peter.parker@example.com"

    page.goto(live_server.url + reverse("fds_donation:donate"))
    page.get_by_role("button", name="5 Euro").click()
    page.get_by_text("monatlich").click()
    page.get_by_text("SEPA-Lastschrift", exact=True).click()
    fill_donation_page(page, donor_email)
    with page.expect_navigation():
        page.get_by_role("button", name="Jetzt spenden").click()

    stripe_sepa_setup.final_event = "invoice.payment_succeeded"

    with stripe_sepa_setup:
        page.locator("#id_iban").fill(STRIPE_TEST_IBANS["success"])
        page.get_by_role("button", name="Jetzt spenden").click()

        page.wait_for_url(DONATION_DONE_URL)

        assert page.get_by_text("Vielen Dank für Deine Spende!").is_visible()
        assert page.get_by_text(donor_email).is_visible()

        print("waiting for webhooks to complete...")

    webhooks = [webhook.name for webhook in stripe_sepa_setup.webhooks_called]
    print(webhooks)

    stripe_event_id = [
        event.event_id
        for event in stripe_sepa_setup.webhooks_called
        if event.name == "payment_intent.succeeded"
    ][0]
    event = stripe.Event.retrieve(stripe_event_id)
    mandate_id = event.data.object.charges.data[
        0
    ].payment_method_details.sepa_debit.mandate
    mandate = stripe.Mandate.retrieve(mandate_id)
    assert mandate.status == "active"
    assert mandate.type == "multi_use"
    assert mandate.payment_method_details.type == "sepa_debit"

    # Wait for webhooks to be processed by live server
    time.sleep(2)
    donation = Donation.objects.filter(
        donor__email=donor_email, amount=5, recurring=True
    ).latest("timestamp")
    payment = donation.payment
    assert payment.status == "confirmed"

    # Modify subscription
    subscription = donation.order.subscription
    old_plan = subscription.plan
    assert old_plan.interval == 1
    page.goto(
        live_server.url
        + reverse(
            "froide_payment:subscription-detail", kwargs={"token": subscription.token}
        )
    )
    page.locator("#id_amount").fill("10")
    page.locator("#id_interval_1").click()
    mail.outbox = []
    page.get_by_role("button", name="Dauerspende ändern").click()
    page.wait_for_load_state("networkidle")

    # Open confirmation link in email
    assert mail.outbox[-1].to[0] == subscription.customer.user_email
    message = mail.outbox[-1]
    match = re.search(r"http://\S+", message.body)
    assert match
    page.goto(match.group(0))
    page.wait_for_load_state("networkidle")

    # Check subscription change
    subscription.refresh_from_db()
    assert subscription.plan != old_plan
    assert subscription.plan.amount == Decimal("10")
    assert subscription.plan.interval == 3
    stripe_sub = stripe.Subscription.retrieve(subscription.remote_reference)
    assert stripe_sub.plan.interval_count == 3
    assert stripe_sub.plan.id == subscription.plan.remote_reference
    assert stripe_sub.trial_end is not None


@pytest.mark.django_db
@pytest.mark.stripe
def test_sepa_once_donation_additional_fields(
    page: Page, live_server, stripe_sepa_setup
):
    donor_email = "peter.parker@example.com"

    page.goto(live_server.url + reverse("fds_donation:donate"))
    page.get_by_role("button", name="5 Euro").click()
    page.get_by_text("SEPA-Lastschrift", exact=True).click()
    fill_donation_page(page, donor_email)
    page.get_by_role("button", name="Jetzt spenden").click()

    stripe_sepa_setup.final_event = "charge.succeeded"

    with stripe_sepa_setup:
        page.locator("#id_iban").fill(STRIPE_TEST_IBANS["additional_fields"])
        page.get_by_role("button", name="Jetzt spenden").click()

        page.get_by_placeholder("Adresse").fill("Teststraße 1")
        page.get_by_placeholder("Ort").fill("Zürich")
        page.get_by_placeholder("Postleitzahl").fill("1234")

        page.get_by_role("button", name="Jetzt spenden").click()

        page.wait_for_url(DONATION_DONE_URL)

        assert page.get_by_text("Vielen Dank für Deine Spende!").is_visible()
        assert page.get_by_text(donor_email).is_visible()

        print("waiting for webhooks to complete...")

    webhooks = [webhook.name for webhook in stripe_sepa_setup.webhooks_called]
    print(webhooks)

    stripe_event_id = [
        event.event_id
        for event in stripe_sepa_setup.webhooks_called
        if event.name == "payment_intent.succeeded"
    ][0]
    event = stripe.Event.retrieve(stripe_event_id)
    mandate_id = event.data.object.charges.data[
        0
    ].payment_method_details.sepa_debit.mandate
    mandate = stripe.Mandate.retrieve(mandate_id)

    assert (mandate.status, mandate.type) in [
        ("inactive", "single_use"),
        ("active", "multi_use"),
    ]
    assert mandate.payment_method_details.type == "sepa_debit"

    # Wait for webhooks to be processed by live server
    time.sleep(2)
    donation = Donation.objects.filter(
        donor__email=donor_email, amount=5, recurring=False
    ).latest("timestamp")
    assert donation.recurring is False
    assert donation.payment.status == "confirmed"
    assert donation.order.subscription is None


@pytest.mark.django_db
@pytest.mark.stripe
def test_sepa_recurring_donation_failed(page: Page, live_server, stripe_sepa_setup):
    donor_email = "peter.parker@example.com"

    page.goto(live_server.url + reverse("fds_donation:donate"))
    page.get_by_role("button", name="5 Euro").click()
    page.get_by_text("monatlich").click()
    page.get_by_text("SEPA-Lastschrift", exact=True).click()
    fill_donation_page(page, donor_email)
    page.get_by_role("button", name="Jetzt spenden").click()

    stripe_sepa_setup.set_final_event("customer.subscription.deleted")
    with stripe_sepa_setup:
        page.locator("#id_iban").fill(STRIPE_TEST_IBANS["failed"])
        page.get_by_role("button", name="Jetzt spenden").click()

        page.wait_for_url(DONATION_DONE_URL)

        assert page.get_by_text("Vielen Dank für Deine Spende!").is_visible()
        assert page.get_by_text(donor_email).is_visible()

        print("waiting for webhooks to complete...")

    webhooks = [webhook.name for webhook in stripe_sepa_setup.webhooks_called]
    print(webhooks)

    stripe_event_id = [
        event.event_id
        for event in stripe_sepa_setup.webhooks_called
        if event.name == "payment_intent.payment_failed"
    ][0]
    event = stripe.Event.retrieve(stripe_event_id)
    charge = event.data.object.charges.data[0]
    assert charge.status == "failed"

    # Wait for webhooks to be processed by live server
    time.sleep(2)
    donation = Donation.objects.filter(
        donor__email=donor_email, amount=5, recurring=True
    ).latest("timestamp")
    payment = donation.payment
    assert payment.status == "error"
    assert donation.amount_received == 0


@pytest.mark.django_db
@pytest.mark.stripe
def test_sepa_once_donation_disputed(page: Page, live_server, stripe_sepa_setup):
    donor_email = "peter.parker@example.com"

    page.goto(live_server.url + reverse("fds_donation:donate"))
    page.get_by_role("button", name="5 Euro").click()
    page.get_by_text("SEPA-Lastschrift", exact=True).click()
    fill_donation_page(page, donor_email)
    page.get_by_role("button", name="Jetzt spenden").click()

    stripe_sepa_setup.final_event = "charge.dispute.closed"

    with stripe_sepa_setup:
        page.locator("#id_iban").fill(STRIPE_TEST_IBANS["disputed"])
        page.get_by_role("button", name="Jetzt spenden").click()

        page.wait_for_url(DONATION_DONE_URL)

        assert page.get_by_text("Vielen Dank für Deine Spende!").is_visible()
        assert page.get_by_text(donor_email).is_visible()

        print("waiting for webhooks to complete...")

    webhooks = [webhook.name for webhook in stripe_sepa_setup.webhooks_called]
    print(webhooks)

    # Wait for webhooks to be processed by live server
    time.sleep(2)
    donation = Donation.objects.filter(
        donor__email=donor_email, amount=5, recurring=False
    ).latest("timestamp")
    payment = donation.payment
    assert payment.status == "rejected"
    assert payment.received_amount == 0
    assert donation.amount_received == 0


@pytest.mark.django_db
@pytest.mark.stripe
def test_creditcard_recurring_donation_success(
    page: Page, live_server, stripe_sepa_setup
):
    donor_email = "peter.parker@example.com"

    page.goto(live_server.url + reverse("fds_donation:donate"))
    page.get_by_role("button", name="5 Euro").click()
    page.get_by_text("monatlich").click()
    page.get_by_text("Kreditkarte", exact=True).click()
    fill_donation_page(page, donor_email)
    page.get_by_role("button", name="Jetzt spenden").click()

    stripe_sepa_setup.final_event = "invoice.payment_succeeded"

    with stripe_sepa_setup:
        frame = page.frame_locator('iframe[name^="__privateStripeFrame"]').first
        frame.locator(".CardField-restWrapper").click()
        frame.get_by_placeholder("Kartennummer").fill(STRIPE_TEST_CARDS["success"])
        next_year = datetime.now().year + 1
        frame.get_by_placeholder("MM/JJ").fill("12 / {}".format(next_year))
        frame.get_by_placeholder("Prüfziffer").fill("123")
        frame.get_by_placeholder("PLZ").click()
        frame.get_by_placeholder("PLZ").fill("12345")

        page.get_by_role("button").click()

        page.wait_for_url(DONATION_DONE_URL)

        assert page.get_by_text("Vielen Dank für Deine Spende!").is_visible()
        assert page.get_by_text(donor_email).is_visible()

        print("waiting for webhooks to complete...")

    webhooks = [webhook.name for webhook in stripe_sepa_setup.webhooks_called]
    print(webhooks)

    # Wait for webhooks to be processed by live server
    time.sleep(2)
    donation = Donation.objects.filter(
        donor__email=donor_email, amount=5, recurring=True
    ).latest("timestamp")
    payment = donation.payment
    assert payment.status == "confirmed"
    assert donation.order.subscription is not None


@pytest.mark.django_db
@pytest.mark.stripe
def test_creditcard_once_donation_success(page: Page, live_server, stripe_sepa_setup):
    donor_email = "peter.parker@example.com"

    page.goto(live_server.url + reverse("fds_donation:donate"))
    page.get_by_role("button", name="5 Euro").click()
    # page.get_by_text("monatlich").click()
    page.get_by_text("Kreditkarte", exact=True).click()
    fill_donation_page(page, donor_email)
    page.get_by_role("button", name="Jetzt spenden").click()

    stripe_sepa_setup.final_event = "charge.succeeded"

    with stripe_sepa_setup:
        frame = page.frame_locator('iframe[name^="__privateStripeFrame"]').first
        frame.locator(".CardField-restWrapper").click()
        frame.get_by_placeholder("Kartennummer").fill(STRIPE_TEST_CARDS["success"])
        next_year = datetime.now().year + 1
        frame.get_by_placeholder("MM/JJ").fill("12 / {}".format(next_year))
        frame.get_by_placeholder("Prüfziffer").fill("123")
        frame.get_by_placeholder("PLZ").click()
        frame.get_by_placeholder("PLZ").fill("12345")

        page.get_by_role("button").click()

        page.wait_for_url(DONATION_DONE_URL)

        assert page.get_by_text("Vielen Dank für Deine Spende!").is_visible()
        assert page.get_by_text(donor_email).is_visible()

        print("waiting for webhooks to complete...")

    webhooks = [webhook.name for webhook in stripe_sepa_setup.webhooks_called]
    print(webhooks)

    # Wait for webhooks to be processed by live server
    time.sleep(2)
    donation = Donation.objects.filter(
        donor__email=donor_email, amount=5, recurring=False
    ).latest("timestamp")
    payment = donation.payment
    assert payment.status == "confirmed"
    assert donation.order.subscription is None
