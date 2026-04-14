import re

from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

import pytest

from fragdenstaat_de.fds_donation.models import Donation, Donor


@pytest.fixture
def donor():
    donor = Donor.objects.create(
        email="test@example.org", email_confirmed=timezone.now()
    )
    Donation.objects.create(donor=donor, amount=10.0, completed=True)
    return donor


other_donor = donor


@pytest.mark.django_db
def test_change_email_flow(client, donor, mailoutbox):
    login_url = donor.get_absolute_login_url()
    response = client.post(login_url)
    assert response.status_code == 302
    assert response.url == reverse("fds_donation:donor")
    response = client.get(reverse("fds_donation:donor-change_email"))
    assert response.status_code == 200

    response = client.post(
        reverse("fds_donation:donor-change_email"),
        data={"email": "newtest@example.org"},
    )
    assert response.status_code == 302
    assert len(mailoutbox) == 1
    mail = mailoutbox[0]
    match = re.search(r"http://.*", mail.body)
    assert match is not None
    url = match.group(0)
    response = client.get(url)
    assert response.status_code == 200

    response = client.post(url)
    assert response.status_code == 302
    assert response.url == reverse("fds_donation:donor")

    donor.refresh_from_db()
    assert donor.email == "newtest@example.org"


@pytest.mark.django_db
def test_change_email_need_login(client):
    response = client.get(reverse("fds_donation:donor-change_email"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("fds_donation:donor-send-login-link"))


@pytest.mark.django_db
def test_change_email_same_email(client, donor, mailoutbox):
    login_url = donor.get_absolute_login_url()
    response = client.post(login_url)
    assert response.status_code == 302
    assert response.url == reverse("fds_donation:donor")
    response = client.get(reverse("fds_donation:donor-change_email"))
    assert response.status_code == 200

    response = client.post(
        reverse("fds_donation:donor-change_email"),
        data={"email": "test@example.org"},
    )
    assert response.status_code == 302
    assert len(mailoutbox) == 0

    donor.refresh_from_db()
    assert donor.email == "test@example.org"


@pytest.mark.django_db
def test_bad_confirm_link(client, donor):
    login_url = donor.get_absolute_login_url()
    response = client.post(login_url)
    assert response.status_code == 302

    url = (
        reverse(
            "fds_donation:donor-confirm_email",
            kwargs={"donor_id": donor.id, "token": "badtoken"},
        )
        + "?email=newtest@example.org"
    )

    response = client.post(url)
    assert response.status_code == 302
    response = client.get(response.url)
    assert response.status_code == 200
    message_list = list(response.context["messages"])
    assert message_list[0].level == messages.WARNING

    donor.refresh_from_db()
    assert donor.email != "newtest@example.org"


@pytest.mark.django_db
def test_donor_merge_on_change(client, donor, other_donor, mailoutbox):
    other_donor.email = "newtest@example.org"
    other_donor.save()

    login_url = donor.get_absolute_login_url()
    response = client.post(login_url)
    assert response.status_code == 302
    assert response.url == reverse("fds_donation:donor")
    response = client.get(reverse("fds_donation:donor-change_email"))
    assert response.status_code == 200

    response = client.post(
        reverse("fds_donation:donor-change_email"),
        data={"email": "newtest@example.org"},
    )
    assert response.status_code == 302
    assert len(mailoutbox) == 1
    mail = mailoutbox[0]
    match = re.search(r"http://.*", mail.body)
    assert match is not None
    url = match.group(0)
    response = client.get(url)
    assert response.status_code == 200

    response = client.post(url)
    assert response.status_code == 302
    assert response.url == reverse("fds_donation:donor")

    donor.refresh_from_db()
    assert donor.email == "newtest@example.org"

    with pytest.raises(Donor.DoesNotExist):
        other_donor.refresh_from_db()

    assert donor.donations.count() == 2


@pytest.mark.django_db
def test_donor_change_email_same_profile(client, donor, other_donor, mailoutbox):
    login_url = donor.get_absolute_login_url()
    response = client.post(login_url)
    assert response.status_code == 302
    assert response.url == reverse("fds_donation:donor")
    response = client.get(reverse("fds_donation:donor-change_email"))
    assert response.status_code == 200

    response = client.post(
        reverse("fds_donation:donor-change_email"),
        data={"email": "newtest@example.org"},
    )
    assert response.status_code == 302
    assert len(mailoutbox) == 1
    mail = mailoutbox[0]
    match = re.search(r"http://.*", mail.body)
    assert match is not None
    url = match.group(0)

    # logout
    response = client.post(reverse("fds_donation:donor-logout"))
    assert response.status_code == 302

    # Does not work, same profile needs to be logged in
    response = client.get(url)
    assert response.status_code == 302
    assert response.url.startswith(reverse("fds_donation:donor-send-login-link"))

    # Try other donor
    other_login_url = other_donor.get_absolute_login_url()
    response = client.post(other_login_url)
    assert response.status_code == 302

    # Also not working
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == reverse("fds_donation:donor")

    response = client.post(url)
    assert response.status_code == 302
    assert response.url == reverse("fds_donation:donor")

    donor.refresh_from_db()
    assert donor.email != "newtest@example.org"
