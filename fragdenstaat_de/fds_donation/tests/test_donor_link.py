import re
import uuid
from urllib.parse import urlencode

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone

import pytest

from froide.account.factories import UserFactory

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
def test_donor_access(client, donor):
    url = donor.get_login_url()

    response = client.post(url)
    assert response.status_code == 302
    assert response.url.endswith("/spenden/spende/ihre-spenden/")
    assert client.session["donor_id"] == donor.id
    response = client.get(response.url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_donor_access_twice(client, donor):
    url = donor.get_login_url()

    response = client.post(url)
    assert response.status_code == 302
    assert response.url.endswith("/spenden/spende/ihre-spenden/")
    assert client.session["donor_id"] == donor.id
    # Logout
    response = client.post(reverse("fds_donation:donor-logout"))
    assert "donor_id" not in client.session
    assert response.status_code == 302

    # Try again
    response = client.post(url)
    assert "donor_id" not in client.session
    assert response.status_code == 302
    assert response.url.endswith(reverse("fds_donation:donor-send-login-link"))


@pytest.mark.django_db
def test_bad_donor_link(client, donor):
    url = reverse(
        "fds_donation:donor-login",
        kwargs={
            "donor_id": donor.id,
            "token": "badtoken",
            "next_path": "/spenden/spende/ihre-spenden/",
        },
    )

    response = client.post(url)
    assert "donor_id" not in client.session
    assert response.status_code == 302
    assert response.url.endswith(reverse("fds_donation:donor-send-login-link"))


@pytest.mark.django_db
def test_bad_donor_user(client, donor):
    dummy_user = UserFactory(username="dummy")
    donor.user = dummy_user
    donor.save()
    url = donor.get_login_url()

    user = UserFactory(username="user")
    client.force_login(user)

    response = client.post(url)
    assert response.status_code == 302
    assert client.session.get("donor_id") is None


@pytest.mark.django_db
def test_bad_donor_user_login_later(client, donor):
    dummy_user = UserFactory(username="dummy")
    donor.user = dummy_user
    donor.save()
    url = donor.get_login_url()

    response = client.post(url)
    assert response.status_code == 302

    user = UserFactory(username="user")
    client.force_login(user)

    response = client.get(reverse("fds_donation:donor"))

    assert response.status_code == 200
    assert client.session.get("donor_id") is not None


@pytest.mark.django_db
def test_correct_donor_user(client, donor):
    dummy_user = UserFactory(username="dummy")
    donor.user = dummy_user
    donor.save()
    url = donor.get_login_url()
    client.force_login(dummy_user)
    response = client.post(url)
    assert response.status_code == 302
    assert response.url == reverse("fds_donation:donor")
    assert client.session.get("donor_id") is None


@pytest.mark.django_db
def test_no_donor_user(client):
    dummy_user = UserFactory(username="dummy")
    client.force_login(dummy_user)
    response = client.get(reverse("fds_donation:donor"))
    assert response.status_code == 302
    assert response.url == "/spenden/"


@pytest.mark.django_db
def test_no_donor(client):
    response = client.get(reverse("fds_donation:donor"))
    assert response.status_code == 302
    assert response.url == reverse("fds_donation:donor-send-login-link")


@pytest.mark.django_db
def test_get_donor_link_bad_email(client, mailoutbox):
    send_link_url = reverse("fds_donation:donor-send-login-link")
    response = client.get(send_link_url)
    assert response.status_code == 200
    response = client.post(send_link_url, data={"email": "bad@example.org"})
    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == "Kein Spendenprofil gefunden"


@pytest.mark.django_db
def test_get_donor_link(client, donor, mailoutbox, settings):
    send_link_url = reverse("fds_donation:donor-send-login-link")
    response = client.post(send_link_url, data={"email": donor.email})
    assert response.status_code == 302
    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == "Zugang zu deinem Spendenprofil bei FragDenStaat"
    url_pattern = re.compile(
        settings.SITE_URL
        + reverse(
            "fds_donation:donor-login",
            kwargs={
                "donor_id": donor.id,
                "token": "TOKEN",
                "next_path": reverse("fds_donation:donor"),
            },
        ).replace("TOKEN", r"[^/]+")
    )
    match = url_pattern.search(mailoutbox[0].body)
    assert match is not None
    login_url = match.group(0)
    response = client.get(login_url)
    assert response.status_code == 200
    response = client.post(login_url)
    assert response.status_code == 302
    assert client.session.get("donor_id") == donor.id


@pytest.mark.django_db
@pytest.mark.parametrize("view_name", ["", "-change", "-donate"])
def test_legacy_donor_redirect(client, view_name):
    legacy_url = reverse(
        f"fds_donation:donor-legacy{view_name}", kwargs={"token": str(uuid.uuid4())}
    )
    response = client.get(legacy_url)
    assert response.status_code == 302
    next_path = urlencode({"next": reverse(f"fds_donation:donor{view_name}")})
    assert next_path in response.url
    assert response.url.startswith(reverse("fds_donation:donor-send-login-link"))


@pytest.mark.django_db
@pytest.mark.parametrize("view_name", ["", "-change", "-donate"])
def test_legacy_donor_manage(client, view_name, donor):
    staff_user = UserFactory(username="staff")
    staff_user.is_staff = True
    staff_user.save()
    permission = Permission.objects.get(
        codename="change_donor",
        content_type=ContentType.objects.get_for_model(Donor),
    )

    send_login_link_url = reverse("fds_donation:donor-send-login-link")

    legacy_url = reverse(
        f"fds_donation:donor-legacy{view_name}", kwargs={"token": str(donor.uuid)}
    )
    response = client.get(legacy_url)
    assert response.status_code == 302
    assert response.headers["Location"].startswith(send_login_link_url)

    client.force_login(staff_user)

    legacy_url = reverse(
        f"fds_donation:donor-legacy{view_name}", kwargs={"token": str(donor.uuid)}
    )
    response = client.get(legacy_url)
    assert response.status_code == 302
    assert response.headers["Location"].startswith(send_login_link_url)

    staff_user.user_permissions.add(permission)

    bad_legacy_url = reverse(
        f"fds_donation:donor-legacy{view_name}", kwargs={"token": str(uuid.uuid4())}
    )
    response = client.get(bad_legacy_url)
    assert response.status_code == 404

    legacy_url = reverse(
        f"fds_donation:donor-legacy{view_name}", kwargs={"token": str(donor.uuid)}
    )
    response = client.get(legacy_url)
    assert response.status_code == 302
    assert response.headers["Location"].startswith(
        reverse(f"fds_donation:donor{view_name}")
    )
    response = client.get(response.headers["Location"])
    assert response.status_code == 200


@pytest.mark.django_db
def test_deduplicate_donor_user(client, donor, other_donor):
    user = UserFactory(username="user")
    donor.user = user
    donor.save()
    other_donor.user = user
    other_donor.save()

    url = reverse("fds_donation:donor")

    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200
    assert client.session.get("donor_id") is None
    assert response.context["donations"].count() == 2
    assert response.context["donor"] == other_donor

    with pytest.raises(Donor.DoesNotExist):
        donor.refresh_from_db()
