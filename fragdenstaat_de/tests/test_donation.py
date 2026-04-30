from django.core import mail
from django.core.management import call_command

import pytest
from playwright.async_api import Page

from fragdenstaat_de.fds_donation.models import Donation


@pytest.fixture(scope="function")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "cms.json")


@pytest.mark.xdist_group(name="sequential")
@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.django_db
async def test_donation_page(page: Page, live_server, django_db_setup):
    mail.outbox = []
    response = await page.goto(live_server.url + "/spenden/spende/spenden/")
    assert response
    assert response.status == 200
    await page.click("text=20 Euro")
    await page.fill("#id_first_name", "Test")
    await page.fill("#id_last_name", "Testor")
    await page.fill("#id_email", "test@example.com")
    await page.click("text=Überweisung")
    await page.click("#id_contact_1")
    await page.click("#id_account_1")
    await page.fill("input[name=test]", "7")
    await page.click("#donate-now")
    assert page.url.startswith(
        live_server.url + "/spenden/spende/spenden/abgeschlossen/"
    )

    donation = Donation.objects.filter(
        donor__first_name="Test",
        donor__last_name="Testor",
        donor__email="test@example.com",
    )[0]
    assert donation.amount == 20
    assert donation.completed is True
    assert donation.received_timestamp is None

    assert len(mail.outbox) == 1
    mail_message = mail.outbox[0]
    assert mail_message.to[0] == "test@example.com"
