import re

from django.urls import reverse

import pytest
from playwright.async_api import Page

from fragdenstaat_de.fds_donation.models import Donation


@pytest.fixture
def banktransfer_setup(settings, live_server):
    """
    Sets up settings to handle payments with paypal via live_server.
    The fixture itself is a context manager that captures webhooks.
    """
    settings.SITE_URL = live_server.url
    settings.ALLOWED_HOSTS = ["*"]


@pytest.mark.asyncio(loop_scope="session")
async def fill_donation_page(page: Page, donor_email):
    await page.get_by_placeholder("Vorname").fill("Peter")
    await page.get_by_placeholder("Nachname").fill("Parker")
    await page.get_by_placeholder("z.B. name@beispiel.de").fill(donor_email)
    await page.get_by_text("Nein, danke.").nth(1).click()
    await page.get_by_text("Nein, danke.").nth(2).click()
    await page.get_by_label("Was ist drei plus vier?").fill("7")


DONATION_DONE_URL = re.compile(r".*spenden/spende/spenden/abgeschlossen/.*")


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.django_db
async def test_banktransfer_once(
    page: Page, live_server, banktransfer_setup, mailoutbox
):
    donor_email = "peter.parker@example.com"

    await page.goto(live_server.url + reverse("fds_donation:donate"))
    await page.get_by_role("button", name="5 Euro").click()
    await page.get_by_text("Überweisung", exact=True).click()
    await fill_donation_page(page, donor_email)

    await page.get_by_role("button", name="Jetzt spenden").click()
    await page.wait_for_url(DONATION_DONE_URL)

    assert await page.get_by_text("Vielen Dank für Deine Spende!").is_visible()
    assert await page.get_by_text(donor_email).is_visible()

    donation = Donation.objects.filter(
        donor__email=donor_email, amount=5, recurring=False, method="banktransfer"
    ).latest("timestamp")
    assert donation.completed is True
    assert donation.received_timestamp is None
    assert donation.payment.status == "pending"
    assert donation.recurrence is None
    message = mailoutbox[0]
    assert message.to[0] == donor_email
    assert "IBAN" in message.body


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.django_db
async def test_banktransfer_recurring(
    page: Page, live_server, banktransfer_setup, mailoutbox
):
    donor_email = "peter.parker@example.com"

    await page.goto(live_server.url + reverse("fds_donation:donate"))
    await page.get_by_role("button", name="5 Euro").click()
    await page.get_by_text("monatlich").click()
    await page.get_by_text("Überweisung", exact=True).click()
    await fill_donation_page(page, donor_email)

    await page.get_by_role("button", name="Jetzt spenden").click()
    await page.wait_for_url(DONATION_DONE_URL)

    assert await page.get_by_text("Vielen Dank für Deine Spende!").is_visible()
    assert await page.get_by_text(donor_email).is_visible()

    donation = Donation.objects.filter(
        donor__email=donor_email, amount=5, recurring=True, method="banktransfer"
    ).latest("timestamp")
    assert donation.completed is True
    assert donation.received_timestamp is None
    assert donation.payment.status == "pending"
    assert donation.recurrence is not None
    message = mailoutbox[0]
    assert message.to[0] == donor_email
    assert "IBAN" in message.body
