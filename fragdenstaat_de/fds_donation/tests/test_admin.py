from datetime import datetime

from django.contrib.admin.sites import AdminSite
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.utils import timezone

import pytest

from froide.account.factories import UserFactory

from ..admin import DonorAdmin, DonorTotalAmountPerYearFilter
from ..models import Donation, Donor


@pytest.fixture
def dummy_user():
    yield UserFactory(username="dummy")


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def donors_with_donations(db):
    donor1 = Donor.objects.create(
        email="donor1@example.com", first_name="John", last_name="Doe"
    )
    donor2 = Donor.objects.create(
        email="donor2@example.com", first_name="Jane", last_name="Smith"
    )
    donor3 = Donor.objects.create(
        email="donor3@example.com", first_name="Bob", last_name="Johnson"
    )

    Donation.objects.create(
        donor=donor1,
        amount=1500,
        received_timestamp=timezone.make_aware(datetime(2024, 1, 1)),
    )
    Donation.objects.create(
        donor=donor2,
        amount=800,
        received_timestamp=timezone.make_aware(datetime(2024, 3, 1)),
    )
    Donation.objects.create(
        donor=donor3,
        amount=300,
        received_timestamp=timezone.make_aware(datetime(2024, 12, 1)),
    )

    return donor1, donor2, donor3


@pytest.fixture
def create_filter():
    donor_admin = DonorAdmin(Donor, AdminSite())

    def _create(request, params):
        return DonorTotalAmountPerYearFilter(request, params, Donor, donor_admin)

    return _create


@pytest.fixture
def request_with_messages(rf, dummy_user):
    def _create(path="/", data=None):
        request = rf.get(path, data or {})
        request.user = dummy_user
        SessionMiddleware(lambda r: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)
        return request

    return _create


@pytest.mark.django_db
def test_exact_amount_filtering(rf, create_filter, donors_with_donations):
    donor1, donor2, donor3 = donors_with_donations

    request = rf.get("/", {"__amount": "800", "__year": "2024"})
    params = {"__amount": ["800"], "__year": ["2024"]}
    filter_instance = create_filter(request, params)

    filtered = filter_instance.queryset(request, Donor.objects.all())

    assert filtered.count() == 1
    assert filtered.first() == donor2


@pytest.mark.django_db
def test_range_amount_filtering(rf, create_filter, donors_with_donations):
    donor1, donor2, donor3 = donors_with_donations

    request = rf.get("/", {"__amount": "500-1000", "__year": "2024"})
    params = {"__amount": ["500-1000"], "__year": ["2024"]}
    filter_instance = create_filter(request, params)

    filtered = filter_instance.queryset(request, Donor.objects.all())

    assert filtered.count() == 1
    assert filtered.first() == donor2


@pytest.mark.django_db
def test_minimum_amount_filtering(rf, create_filter, donors_with_donations):
    donor1, donor2, donor3 = donors_with_donations

    request = rf.get("/", {"__amount": "1000-", "__year": "2024"})
    params = {"__amount": ["1000-"], "__year": ["2024"]}
    filter_instance = create_filter(request, params)

    filtered = filter_instance.queryset(request, Donor.objects.all())

    assert filtered.count() == 1
    assert filtered.first() == donor1


@pytest.mark.django_db
def test_maximum_amount_filtering(rf, create_filter, donors_with_donations):
    donor1, donor2, donor3 = donors_with_donations

    request = rf.get("/", {"__amount": "-500", "__year": "2024"})
    params = {"__amount": ["-500"], "__year": ["2024"]}
    filter_instance = create_filter(request, params)

    filtered = filter_instance.queryset(request, Donor.objects.all())

    assert filtered.count() == 1
    assert filtered.first() == donor3


@pytest.mark.django_db
def test_empty_inputs_return_all(rf, create_filter, donors_with_donations):
    # Empty amount
    request = rf.get("/", {"__amount": "", "__year": "2024"})
    params = {"__amount": [""], "__year": ["2024"]}
    filter_instance = create_filter(request, params)
    filtered = filter_instance.queryset(request, Donor.objects.all())
    assert filtered.count() == 3

    # Empty year
    request = rf.get("/", {"__amount": "1000", "__year": ""})
    params = {"__amount": ["1000"], "__year": [""]}
    filter_instance = create_filter(request, params)
    filtered = filter_instance.queryset(request, Donor.objects.all())
    assert filtered.count() == 3


@pytest.mark.django_db
def test_invalid_amount_shows_error(
    request_with_messages, create_filter, donors_with_donations
):
    request = request_with_messages("/", {"__amount": "abc", "__year": "2024"})
    params = {"__amount": ["abc"], "__year": ["2024"]}
    filter_instance = create_filter(request, params)

    filtered = filter_instance.queryset(request, Donor.objects.all())

    assert filtered.count() == 3
    messages_list = list(get_messages(request))
    assert len(messages_list) == 1
    assert "abc" in str(messages_list[0])
