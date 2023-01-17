from django.core import mail
from django.core.management import call_command

import pytest
from fragdenstaat_de.fds_donation.models import Donation


@pytest.fixture(scope="function")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "cms.json")


@pytest.mark.django_db
def test_donation_page(page, live_server, django_db_setup):
    mail.outbox = []
    response = page.goto(live_server.url + "/spenden/spende/spenden/")
    assert response.status == 200
    page.click("text=20 Euro")
    page.fill("#id_first_name", "Test")
    page.fill("#id_last_name", "Testor")
    page.fill("#id_email", "test@example.com")
    page.click("text=Überweisung")
    page.click("#id_contact_1")
    page.click("#id_account_1")
    page.fill("input[name=test]", "7")
    page.click("#donate-now")
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
