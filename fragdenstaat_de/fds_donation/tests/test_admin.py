from datetime import datetime

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.utils import timezone

from ..admin import DonorAdmin, DonorTotalAmountPerYearFilter
from ..models import Donation, Donor

User = get_user_model()


class DonorTotalAmountPerYearFilterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.donor_admin = DonorAdmin(Donor, self.admin_site)

        # Setup user for messages
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )

        # Create test donors with donations in 2024
        self.donor1 = Donor.objects.create(
            email="donor1@example.com", first_name="John", last_name="Doe"
        )
        self.donor2 = Donor.objects.create(
            email="donor2@example.com", first_name="Jane", last_name="Smith"
        )
        self.donor3 = Donor.objects.create(
            email="donor3@example.com", first_name="Bob", last_name="Johnson"
        )

        # Create donations: donor1=1500, donor2=800, donor3=300 in 2024
        Donation.objects.create(
            donor=self.donor1,
            amount=1500,
            received_timestamp=timezone.make_aware(datetime(2024, 1, 1)),
        )
        Donation.objects.create(
            donor=self.donor2,
            amount=800,
            received_timestamp=timezone.make_aware(datetime(2024, 3, 1)),
        )
        Donation.objects.create(
            donor=self.donor3,
            amount=300,
            received_timestamp=timezone.make_aware(datetime(2024, 12, 1)),
        )

    def _create_filter_with_params(self, request, params):
        """Helper to create filter with proper params dict"""
        return DonorTotalAmountPerYearFilter(request, params, Donor, self.donor_admin)

    def _create_request_with_messages(self, path="/", data=None):
        """Create a request with message framework support"""
        request = self.factory.get(path, data or {})
        request.user = self.user
        SessionMiddleware(lambda r: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)
        return request

    def test_exact_amount_filtering(self):
        """Test filtering by exact amount"""
        request = self.factory.get("/", {"__amount": "800", "__year": "2024"})
        params = {"__amount": ["800"], "__year": ["2024"]}
        filter_instance = self._create_filter_with_params(request, params)

        filtered = filter_instance.queryset(request, Donor.objects.all())

        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first(), self.donor2)

    def test_range_amount_filtering(self):
        """Test filtering by amount range"""
        request = self.factory.get("/", {"__amount": "500-1000", "__year": "2024"})
        params = {"__amount": ["500-1000"], "__year": ["2024"]}
        filter_instance = self._create_filter_with_params(request, params)

        filtered = filter_instance.queryset(request, Donor.objects.all())

        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first(), self.donor2)

    def test_minimum_amount_filtering(self):
        """Test filtering by minimum amount (1000- format)"""
        request = self.factory.get("/", {"__amount": "1000-", "__year": "2024"})
        params = {"__amount": ["1000-"], "__year": ["2024"]}
        filter_instance = self._create_filter_with_params(request, params)

        filtered = filter_instance.queryset(request, Donor.objects.all())

        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first(), self.donor1)

    def test_maximum_amount_filtering(self):
        """Test filtering by maximum amount (-500 format)"""
        request = self.factory.get("/", {"__amount": "-500", "__year": "2024"})
        params = {"__amount": ["-500"], "__year": ["2024"]}
        filter_instance = self._create_filter_with_params(request, params)

        filtered = filter_instance.queryset(request, Donor.objects.all())

        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first(), self.donor3)

    def test_empty_inputs_return_all(self):
        """Test that empty amount or year returns unfiltered results"""
        # Empty amount
        request = self.factory.get("/", {"__amount": "", "__year": "2024"})
        params = {"__amount": [""], "__year": ["2024"]}
        filter_instance = self._create_filter_with_params(request, params)
        filtered = filter_instance.queryset(request, Donor.objects.all())
        self.assertEqual(filtered.count(), 3)

        # Empty year
        request = self.factory.get("/", {"__amount": "1000", "__year": ""})
        params = {"__amount": ["1000"], "__year": [""]}
        filter_instance = self._create_filter_with_params(request, params)
        filtered = filter_instance.queryset(request, Donor.objects.all())
        self.assertEqual(filtered.count(), 3)

    def test_invalid_amount_shows_error(self):
        """Test that invalid amount format shows error message"""
        request = self._create_request_with_messages(
            "/", {"__amount": "abc", "__year": "2024"}
        )
        params = {"__amount": ["abc"], "__year": ["2024"]}
        filter_instance = self._create_filter_with_params(request, params)

        filtered = filter_instance.queryset(request, Donor.objects.all())

        # Should return unfiltered queryset and show error
        self.assertEqual(filtered.count(), 3)
        messages_list = list(get_messages(request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("abc", str(messages_list[0]))
