import os
import re
import time

from django.urls import reverse

import payments.core
import pytest
from fragdenstaat_de.fds_donation.models import Donation
from playwright.sync_api import Page

from .utils import ProcessReader


class PaypalWebhookForwarder:
    WEBHOOK_URL_RE = re.compile(r"https://\w+.serveo.net")

    def __init__(self, forward_url: str):
        forward_url = forward_url.replace("http://", "")
        host, path = forward_url.split("/", 1)
        self.forward_host = host
        self.forward_path = "/" + path
        self.webhook_url = None
        self.paypal_webhook_id = None
        self.max_request_count = 2

    def setup_webhook(self):
        process_args = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-n",  # Redirect stdin from /dev/null
            "-T",  # Disable pseudo-tty allocation
            "-R",
            "80:{}".format(self.forward_host),
            # Some guys forwarding service because Paypal doesn't have a cli like stripe
            "serveo.net",
        ]
        self.proc = ProcessReader(process_args)
        self.proc.start()
        line = self.proc.readline()
        match = self.WEBHOOK_URL_RE.search(line)
        if match:
            self.webhook_url = match.group(0)
        if self.webhook_url is None:
            raise Exception("Could not find webhook URL")
        self.set_webhook_on_paypal(self.webhook_url)

    def set_webhook_on_paypal(self, webhook_url):
        paypal_provider = payments.core.provider_factory("paypal")
        assert "sandbox" in paypal_provider.endpoint

        response = paypal_provider.post_api(
            "{}/v1/notifications/webhooks".format(paypal_provider.endpoint),
            {
                "url": "{webhook_url}{path}".format(
                    webhook_url=webhook_url, path=self.forward_path
                ),
                "event_types": [
                    {"name": "*"},
                ],
            },
        )
        self.paypal_webhook_id = response["id"]

    def delete_webhook_on_paypal(self):
        paypal_provider = payments.core.provider_factory("paypal")
        assert "sandbox" in paypal_provider.endpoint

        paypal_provider.post_api(
            "{}/v1/notifications/webhooks/{}".format(
                paypal_provider.endpoint, self.paypal_webhook_id
            ),
            None,
            method="DELETE",
        )

    def __enter__(self):
        self.setup_webhook()

    def __exit__(self, exc_type, exc_val, exc_tb):
        HTTP_RE = re.compile(r"HTTP request from")
        http_request_count = 0
        try:
            if exc_val is None:
                while True:
                    line = self.proc.readline()
                    print(repr(line.encode("utf-8")))
                    if HTTP_RE.search(line):
                        http_request_count += 1
                    if http_request_count >= self.max_request_count:
                        break
        finally:
            self.delete_webhook_on_paypal()
            self.proc.stop()


@pytest.fixture
def paypal_setup(settings, live_server, monkeypatch):
    """
    Sets up settings to handle payments with paypal via live_server.
    The fixture itself is a context manager that captures webhooks.
    """
    settings.SITE_URL = live_server.url
    settings.ALLOWED_HOSTS = ["*"]
    # PAYMENT_HOST setting is copied to module level on import, need to patch it
    monkeypatch.setattr(
        payments.core, "PAYMENT_HOST", live_server.url.replace("http://", "")
    )

    webhook_url = live_server.url + "/payments/process/paypal/"
    forwarder = PaypalWebhookForwarder(webhook_url)

    yield forwarder


def fill_donation_page(page: Page, donor_email):
    page.get_by_placeholder("Vorname").fill("Peter")
    page.get_by_placeholder("Nachname").fill("Parker")
    page.get_by_placeholder("z.B. name@beispiel.de").fill(donor_email)
    page.get_by_text("Nein, danke.").nth(1).click()
    page.get_by_text("Nein, danke.").nth(2).click()
    page.get_by_label("Was ist drei plus vier?").fill("7")


def login_paypal(page: Page):
    test_account = os.environ["PAYPAL_TEST_ACCOUNT"]
    test_password = os.environ["PAYPAL_TEST_PASSWORD"]
    page.locator("#email").fill(test_account)
    page.locator("#btnNext").click()
    page.locator("#password").fill(test_password)
    page.locator("#btnLogin").click()


@pytest.mark.django_db
@pytest.mark.paypal
def test_paypal_once(page: Page, live_server, paypal_setup):
    donor_email = "peter.parker@example.com"

    page.goto(live_server.url + reverse("fds_donation:donate"))
    page.get_by_role("button", name="5 Euro").click()
    page.get_by_text("Paypal", exact=True).click()
    fill_donation_page(page, donor_email)

    page.get_by_role("button", name="Jetzt spenden").click()

    login_paypal(page)

    donation = Donation.objects.filter(
        donor__email=donor_email, amount=5, recurring=False, method="paypal"
    ).latest("timestamp")
    assert donation.received_timestamp is None
    assert donation.payment.status == "input"

    # Checkout order approved + payment capture completed
    paypal_setup.max_request_count = 2
    with paypal_setup:
        page.get_by_test_id("submit-button-initial").click()
        page.wait_for_url("**spenden/spende/spenden/abgeschlossen/**")

        assert page.get_by_text("Vielen Dank für Ihre Spende!").is_visible()
        assert page.get_by_text(donor_email).is_visible()

        print("Waiting for webhooks...")

    donation.refresh_from_db()
    assert donation.completed is True
    assert donation.received_timestamp is not None
    payment = donation.payment
    assert payment.status == "confirmed"


@pytest.mark.django_db
@pytest.mark.paypal
def test_paypal_recurring(page: Page, live_server, paypal_setup):
    donor_email = "peter.parker@example.com"

    page.goto(live_server.url + reverse("fds_donation:donate"))
    page.get_by_role("button", name="5 Euro").click()
    page.get_by_text("monatlich").click()
    page.get_by_text("Paypal", exact=True).click()
    fill_donation_page(page, donor_email)

    # Sometimes: Billing plan created + catalog product created
    # Always: billing subscription created + payment sale completed + billing subscription activated
    paypal_setup.max_request_count = 5
    with paypal_setup:
        page.get_by_role("button", name="Jetzt spenden").click()

        login_paypal(page)

        donation = Donation.objects.filter(
            donor__email=donor_email, amount=5, recurring=True, method="paypal"
        ).latest("timestamp")
        assert donation.received_timestamp is None
        assert donation.payment.status != "pending"
        assert donation.payment.status != "confirmed"

        page.locator('[data-test-id="continueButton"]').click()

        page.wait_for_url("**spenden/spende/spenden/abgeschlossen/**")

        assert page.get_by_text("Vielen Dank für Ihre Spende!").is_visible()
        assert page.get_by_text(donor_email).is_visible()

        print("Waiting for webhooks...")

    time.sleep(2)
    donation.refresh_from_db()
    assert donation.completed is True
    assert donation.received_timestamp is not None
    payment = donation.payment
    assert donation.order.subscription_id is not None
    assert payment.status == "confirmed"


@pytest.mark.django_db
@pytest.mark.paypal
def test_paypal_cancel(page: Page, live_server, paypal_setup):
    donor_email = "peter.parker@example.com"

    page.goto(live_server.url + reverse("fds_donation:donate"))
    page.get_by_role("button", name="5 Euro").click()
    page.get_by_text("Paypal", exact=True).click()
    fill_donation_page(page, donor_email)

    page.get_by_role("button", name="Jetzt spenden").click()

    login_paypal(page)

    donation = Donation.objects.filter(
        donor__email=donor_email, amount=5, recurring=False, method="paypal"
    ).latest("timestamp")
    assert donation.received_timestamp is None
    assert donation.payment.status != "pending"
    assert donation.payment.status != "confirmed"
    page.get_by_test_id("cancel-link").click()
    page.wait_for_url("**spenden/spende/spenden/fehlgeschlagen/**")

    assert page.get_by_text("Spende fehlgeschlagen!").is_visible()

    donation.refresh_from_db()
    assert donation.completed is False
    assert donation.received_timestamp is None
