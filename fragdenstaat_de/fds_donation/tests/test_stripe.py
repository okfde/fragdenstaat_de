import logging
import re
import subprocess
import time
import zoneinfo
from collections import namedtuple
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core import mail
from django.urls import reverse

import froide_payment.provider.stripe
import payments.core
import pytest
import stripe
from playwright.sync_api import Page

from fragdenstaat_de.fds_donation.forms import QuickDonationForm
from fragdenstaat_de.fds_donation.models import Donation

from .utils import ProcessReader

WebhookEvent = namedtuple("WebhookEvent", ["timestamp", "name", "event_id"])
WebhookDelivered = namedtuple("WebhookDelivered", ["status_code", "event_id"])

STRIPE_TEST_IBANS = {
    "success": "DE89370400440532013000",
    "success_delayed": "DE08370400440532013003",
    "failed": "DE62370400440532013001",
    "disputed": "DE35370400440532013002",
    "additional_fields": "CH9300762011623852957",
}
STRIPE_TEST_CARDS = {
    "success": "4242424242424242",
    "declined": "4000000000000002",
}


WH_EVENT_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+-->\s+([\w\.]+)\s+\[(\w+)\]"
)
WH_DELIVERED_RE = re.compile(r"<--\s+\[([\d]+)\]\s+POST\s+[^ ]+\s+\[([^\]]+)\]")


class StripeWebhookForwarder:
    def __init__(self, secret_key: str, forward_url: str):
        self.secret_key = secret_key
        self.forward_url = forward_url.replace("http://", "")
        self.webhooks_called = None
        self.webhooks_delivered = None
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

    @contextmanager
    def wait_for_events(self, events: list[str]):
        event_set = set(events)
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
        self.webhooks_called = []
        self.webhooks_delivered = []

        try:
            yield
        except Exception as e:
            self.proc.stop()
            raise e

        try:
            while True:
                line = self.proc.readline()
                webhook_events = self.make_webhook_events(line)
                webhook_deliveries = self.make_webhook_deliveries(line)
                logging.debug(
                    "line: %s, events: %s, deliveries: %s",
                    line,
                    webhook_events,
                    webhook_deliveries,
                )
                self.webhooks_called.extend(webhook_events)
                self.webhooks_delivered.extend(webhook_deliveries)

                event_names = {ev.event_id: ev.name for ev in self.webhooks_called}
                called_event_names = {ev.name for ev in self.webhooks_called}
                delivered_event_names = {
                    event_names[dl.event_id] for dl in self.webhooks_delivered
                }
                logging.info(
                    f"{event_set=} {called_event_names=} {delivered_event_names=}"
                )

                delivered_all_events = len(event_set - delivered_event_names) == 0
                if delivered_all_events:
                    break
        finally:
            self.proc.stop()

    def make_webhook_deliveries(self, log):
        return [WebhookDelivered(*m.groups()) for m in WH_DELIVERED_RE.finditer(log)]

    def make_webhook_events(self, log: str):
        return [WebhookEvent(*m.groups()) for m in WH_EVENT_RE.finditer(log)]


@pytest.fixture(autouse=True)
def skip_stripe_if_no_key(request, settings):
    if request.node.get_closest_marker("stripe"):
        secret_key = settings.PAYMENT_VARIANTS["sepa"][1]["secret_key"]
        if not secret_key:
            raise RuntimeError("skipped stripe test because stripe key is not set")


@pytest.fixture(autouse=True)
def skip_stripe_if_no_cli(request):
    if request.node.get_closest_marker("stripe"):
        import shutil

        if not shutil.which("stripe"):
            raise RuntimeError(
                "Stripe CLI is not installed. "
                "Please install the Stripe CLI: https://stripe.com/docs/stripe-cli"
            )


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

    with stripe_sepa_setup.wait_for_events(["invoice.payment_succeeded"]):
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

    # Change IBAN
    page.goto(
        live_server.url
        + reverse(
            "froide_payment:subscription-detail", kwargs={"token": subscription.token}
        )
    )
    page.locator("#id_iban").fill(STRIPE_TEST_IBANS["success_delayed"])
    page.get_by_role("button", name="IBAN ändern").click()
    page.wait_for_selector(".show.alert-dismissible")
    assert page.get_by_text("wurde aktualisiert")

    stripe_sub = stripe.Subscription.retrieve(subscription.remote_reference)
    stripe_pm_id = stripe_sub.default_payment_method
    stripe_pm = stripe.PaymentMethod.retrieve(stripe_pm_id)
    assert stripe_pm["sepa_debit"]["last4"] == STRIPE_TEST_IBANS["success_delayed"][-4:]
    stripe_customer = stripe.Customer.retrieve(stripe_sub.customer)
    assert stripe_customer.invoice_settings.default_payment_method == stripe_pm_id


class StripeTimeMover:
    def __init__(self, time_machine):
        self.time_machine = time_machine
        self.time_machine.move_to(datetime(2025, 1, 1))
        self.test_clock = stripe.test_helpers.TestClock.create(
            frozen_time=int(time.time()),
        ).id

    def move_days(self, days: float):
        logging.info(f"shifting time by {days} days")
        self.time_machine.shift(timedelta(days=days))
        _ = stripe.test_helpers.TestClock.advance(
            self.test_clock,
            frozen_time=int(time.time()),
        )


@pytest.fixture
def stripe_mocked_time(time_machine, monkeypatch):
    time_mover = StripeTimeMover(time_machine)

    # monkey-patch stripe customer creation to use test-clock
    old_customer_create = stripe.Customer.create

    def customer_create_with_test_clock(*args, **kwargs):
        return old_customer_create(*args, **kwargs, test_clock=time_mover.test_clock)

    with monkeypatch.context() as m:
        m.setattr(stripe.Customer, "create", customer_create_with_test_clock)
        yield time_mover

    stripe.test_helpers.TestClock.delete(time_mover.test_clock)


@pytest.mark.django_db
@pytest.mark.stripe
def test_sepa_shorten_recurring_interval(
    page: Page, live_server, stripe_sepa_setup, stripe_mocked_time
):
    donor_email = "peter.parker@example.com"

    page.goto(live_server.url + reverse("fds_donation:donate"))
    page.get_by_role("button", name="5 Euro").click()
    page.get_by_text("jährlich", exact=True).click()
    page.get_by_text("SEPA-Lastschrift", exact=True).click()
    fill_donation_page(page, donor_email)
    with page.expect_navigation():
        page.get_by_role("button", name="Jetzt spenden").click()

    with stripe_sepa_setup.wait_for_events(["invoice.payment_succeeded"]):
        page.locator("#id_iban").fill(STRIPE_TEST_IBANS["success"])
        page.get_by_role("button", name="Jetzt spenden").click()

        page.wait_for_url(DONATION_DONE_URL)

        assert page.get_by_text("Vielen Dank für Deine Spende!").is_visible()
        assert page.get_by_text(donor_email).is_visible()

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

    time.sleep(2)
    donation = Donation.objects.filter(
        donor__email=donor_email, amount=5, recurring=True
    ).latest("timestamp")
    payment = donation.payment
    assert payment.status == "confirmed"

    # Advance time a bit more than a month
    with stripe_sepa_setup.wait_for_events(["test_helpers.test_clock.ready"]):
        stripe_mocked_time.move_days(32)

    with stripe_sepa_setup.wait_for_events(["invoice.payment_succeeded"]):
        # Modify subscription (now monthly, 10€, changes 5 days in the future)
        subscription = donation.order.subscription
        old_plan = subscription.plan
        last_order = subscription.get_last_order()

        assert old_plan.interval == 12

        next_date = date.today() + timedelta(days=5)
        assert last_order.service_end.date() > next_date

        page.goto(
            live_server.url
            + reverse(
                "froide_payment:subscription-detail",
                kwargs={"token": subscription.token},
            )
        )
        page.locator("#id_amount").fill("10")
        page.get_by_text("monatlich").click()
        page.locator("#id_next_date").fill(next_date.strftime("%Y-%m-%d"))
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

        logging.info("waiting for webhooks to complete")

    # Check subscription change
    subscription.refresh_from_db()
    assert subscription.plan.interval == 1
    stripe_sub = stripe.Subscription.retrieve(subscription.remote_reference)
    assert stripe_sub.plan.interval_count == 1
    assert stripe_sub.plan.id == subscription.plan.remote_reference
    assert stripe_sub.trial_start is not None
    assert stripe_sub.trial_end is not None
    trial_end_date = datetime.fromtimestamp(
        stripe_sub.trial_end, tz=zoneinfo.ZoneInfo("UTC")
    ).date()
    assert trial_end_date == next_date
    last_order.refresh_from_db()
    assert last_order.service_end.date() <= trial_end_date

    # Advance time until after the payment
    stripe_sepa_setup.final_event = "test_helpers.test_clock.ready"
    with stripe_sepa_setup.wait_for_events(
        [
            "test_helpers.test_clock.ready",
            "invoice.payment_succeeded",
            "payment_intent.succeeded",
        ]
    ):
        logging.info("advance time until after the payment")
        stripe_mocked_time.move_days(10)

    assert subscription.orders.count() == 2
    order = subscription.get_last_order()
    assert order.service_start.date() == trial_end_date
    assert order.payments.count() == 1
    payment = order.payments.first()
    assert payment.captured_amount == 10

    # Advance time by a month
    with stripe_sepa_setup.wait_for_events(
        [
            "test_helpers.test_clock.ready",
            "invoice.payment_succeeded",
            "payment_intent.succeeded",
        ]
    ):
        logging.info("advance time by a month")
        stripe_mocked_time.move_days(31)

    assert subscription.orders.count() == 3
    order = subscription.get_last_order()
    assert order.service_start.date() > trial_end_date
    assert order.payments.count() == 1

    payment = order.payments.first()
    assert payment.captured_amount == 10


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

    with stripe_sepa_setup.wait_for_events(["charge.succeeded"]):
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

    with stripe_sepa_setup.wait_for_events(["customer.subscription.deleted"]):
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

    with stripe_sepa_setup.wait_for_events(["charge.dispute.closed"]):
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

    with stripe_sepa_setup.wait_for_events(["invoice.payment_succeeded"]):
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

    with stripe_sepa_setup.wait_for_events(["charge.succeeded"]):
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


@pytest.mark.django_db
@pytest.mark.stripe
def test_quick_donation(client, unsuspicious):
    path = reverse("fds_donation:donate")
    email = "testing@example.com"

    def post():
        return client.post(
            path,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
            data={
                "amount": "15.00",
                "interval": "0",
                "first_name": "John",
                "last_name": "Doe",
                "email": email,
            },
        )

    for _ in range(QuickDonationForm.SPAM_PROTECTION["action_limit"] + 1):
        response = post()
        assert response.status_code == 200
    donation = Donation.objects.filter(donor__email=email).last()
    assert donation.amount == 15.00
    assert donation.completed is False

    # Spam protection kicks in
    response = post()
    assert response.status_code == 400
