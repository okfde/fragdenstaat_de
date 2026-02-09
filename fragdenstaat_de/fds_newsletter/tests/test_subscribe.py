import re
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

import pytest

from froide.foirequest.tests.factories import UserFactory

from fragdenstaat_de.fds_newsletter.utils import subscribe

from ..listeners import (
    activate_newsletter_subscription,
    cancel_user,
    handle_bounce,
    handle_unsubscribe,
    merge_user,
    subscribe_follower,
    user_email_changed,
)
from ..models import Newsletter, Subscriber

User = get_user_model()

SPAM_DISABLED_CONFIG = dict(settings.FROIDE_CONFIG)
SPAM_DISABLED_CONFIG["spam_protection"] = False


@override_settings(FROIDE_CONFIG=SPAM_DISABLED_CONFIG)
class NewsletterSubscriberTest(TestCase):
    """
    States:
    - User logged in or not
    - Already subscribed via email
    - Already subscribed via user

    Actions:
    - subscribe email
    - subscribe email with user
    - activate user
    - merge user
    - delete user
    - email bounced
    - unsubscribe callback
    """

    @classmethod
    def setUpTestData(cls):
        cls.nl = Newsletter.objects.create(slug=settings.DEFAULT_NEWSLETTER)
        cls.email_1 = "one@example.com"
        cls.user = UserFactory.create(email=cls.email_1)
        cls.email_2 = "two@example.com"

    def test_default_newsletter_subscription(self):
        mail.outbox = []
        response = self.client.post(
            reverse("newsletter_subscribe_request"),
            data={"email": self.email_2, "reference": "test"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Subscriber.objects.filter(
                newsletter=self.nl,
                email=self.email_2,
                subscribed=None,
                unsubscribed=None,
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        match = re.search(r"://[^/]+(/.*)", message.body)
        response = self.client.get(match.group(1))
        self.assertEqual(response.status_code, 302)
        subscriber = Subscriber.objects.get(
            newsletter=self.nl, email=self.email_2, subscribed__isnull=False
        )
        self.assertEqual(subscriber.reference, "test")
        self.assertEqual(subscriber.user, None)

    def test_default_newsletter_subscription_ajax(self):
        mail.outbox = []
        response = self.client.post(
            reverse("newsletter_ajax_subscribe_request"),
            data={"email": self.email_2, "reference": "test"},
            headers={
                "x-requested-with": "XMLHttpRequest",
                "origin": "http://testserver",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Subscriber.objects.filter(
                newsletter=self.nl,
                email=self.email_2,
                subscribed=None,
                unsubscribed=None,
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        match = re.search(r"://[^/]+(/.*)", message.body)
        response = self.client.get(match.group(1))
        self.assertEqual(response.status_code, 302)
        subscriber = Subscriber.objects.get(
            newsletter=self.nl, email=self.email_2, subscribed__isnull=False
        )
        self.assertEqual(subscriber.reference, "test")
        self.assertEqual(subscriber.user, None)

    def test_newsletter_subscription_existing_user_with_email(self):
        response = self.client.post(
            reverse("newsletter_subscribe_request"),
            data={"email": self.email_1, "reference": "test"},
        )
        self.assertEqual(response.status_code, 302)

        subscriber = Subscriber.objects.get(
            newsletter=self.nl, email=self.email_1, subscribed=None, unsubscribed=None
        )
        self.assertEqual(len(mail.outbox), 1)
        # confirm subscription
        subscriber.subscribe()
        subscriber.refresh_from_db()
        self.assertIsNotNone(subscriber.subscribed)
        self.assertEqual(subscriber.user, self.user)
        self.assertIsNone(subscriber.email)

    def test_newsletter_subscription_existing_user_with_email_ajax(self):
        response = self.client.post(
            reverse("newsletter_ajax_subscribe_request"),
            data={"email": self.email_1, "reference": "test"},
            headers={
                "x-requested-with": "XMLHttpRequest",
                "origin": "http://testserver",
            },
        )
        self.assertEqual(response.status_code, 200)

        subscriber = Subscriber.objects.get(
            newsletter=self.nl, email=self.email_1, subscribed=None, unsubscribed=None
        )
        self.assertEqual(len(mail.outbox), 1)
        # confirm subscription
        subscriber.subscribe()
        subscriber.refresh_from_db()
        self.assertIsNotNone(subscriber.subscribed)
        self.assertEqual(subscriber.user, self.user)
        self.assertIsNone(subscriber.email)

    def test_newsletter_subscription_existing_user_subscriber_with_email(self):
        self.client.logout()
        mail.outbox = []
        Subscriber.objects.create(
            newsletter=self.nl, user=self.user, subscribed=timezone.now()
        )
        response = self.client.post(
            reverse("newsletter_subscribe_request"),
            data={"email": self.email_1, "reference": "test"},
        )
        self.assertEqual(response.status_code, 302)
        # Reminder already subscribed email
        self.assertEqual(len(mail.outbox), 1)
        # Email subscriber not present, because of user
        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                email=self.email_1,
            ).exists()
        )

    def test_newsletter_subscription_existing_user_subscriber_with_email_ajax(self):
        self.client.logout()
        mail.outbox = []
        Subscriber.objects.create(
            newsletter=self.nl, user=self.user, subscribed=timezone.now()
        )
        response = self.client.post(
            reverse("newsletter_ajax_subscribe_request"),
            data={"email": self.email_1, "reference": "test"},
            headers={
                "x-requested-with": "XMLHttpRequest",
                "origin": "http://testserver",
            },
        )
        self.assertEqual(response.status_code, 200)
        # Reminder already subscribed email
        self.assertEqual(len(mail.outbox), 1)
        # Email subscriber not present, because of user
        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                email=self.email_1,
            ).exists()
        )

    def test_newsletter_subscription_logged_in_same_email(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("newsletter_subscribe_request"),
            data={"email": self.email_1, "reference": "test"},
        )
        self.assertEqual(response.status_code, 302)

        subscriber = Subscriber.objects.get(
            newsletter=self.nl,
            user=self.user,
        )
        self.assertIsNotNone(subscriber.subscribed)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Willkommen zu unserem Newsletter")

    def test_newsletter_subscription_logged_in_same_email_ajax(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("newsletter_ajax_subscribe_request"),
            data={"email": self.email_1, "reference": "test"},
            headers={
                "x-requested-with": "XMLHttpRequest",
                "origin": "http://testserver",
            },
        )
        self.assertEqual(response.status_code, 200)

        subscriber = Subscriber.objects.get(
            newsletter=self.nl,
            user=self.user,
        )
        self.assertIsNotNone(subscriber.subscribed)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Willkommen zu unserem Newsletter")

    def test_newsletter_subscription_logged_in_same_email_ajax_origin(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("newsletter_ajax_subscribe_request"),
            data={"email": self.email_1, "reference": "test"},
            headers={
                "x-requested-with": "XMLHttpRequest",
                "origin": "null",
            },
        )
        self.assertEqual(response.status_code, 200)

        subscriber = Subscriber.objects.get(
            newsletter=self.nl,
            email=self.email_1,
        )
        self.assertIsNone(subscriber.subscribed)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        match = re.search(r"://[^/]+(/.*)", message.body)
        response = self.client.get(match.group(1))
        self.assertEqual(response.status_code, 302)
        subscriber = Subscriber.objects.get(
            newsletter=self.nl,
            user=self.user,
            email=None,
            subscribed__isnull=False,
        )
        self.assertEqual(subscriber.reference, "test")
        self.assertEqual(subscriber.user, self.user)

    def test_newsletter_subscription_logged_in_different_email(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("newsletter_subscribe_request"),
            data={"email": self.email_2, "reference": "test"},
        )
        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=self.user,
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        subscriber = Subscriber.objects.get(
            newsletter=self.nl,
            email=self.email_2,
        )
        self.assertIsNone(subscriber.subscribed)
        subscriber.subscribe()
        self.assertIsNotNone(subscriber.subscribed)
        self.assertIsNone(subscriber.user)

    def test_newsletter_email_subscription_activate_account(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            reverse("newsletter_subscribe_request"),
            data={"email": self.email_1, "reference": "test"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=self.user,
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        subscriber = Subscriber.objects.get(
            newsletter=self.nl,
            email=self.email_1,
        )
        # Activate user before confirming subscription
        self.user.is_active = True
        self.user.save()
        activate_newsletter_subscription(self.user)

        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=self.user,
            ).exists()
        )
        subscriber.refresh_from_db()
        self.assertIsNone(subscriber.user)
        self.assertIsNone(subscriber.subscribed)

        subscriber.subscribe()
        self.assertIsNotNone(subscriber.user)
        self.assertIsNotNone(subscriber.subscribed)

    def test_newsletter_email_subscription_activate_account_later(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            reverse("newsletter_subscribe_request"),
            data={"email": self.email_1, "reference": "test"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=self.user,
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        subscriber = Subscriber.objects.get(
            newsletter=self.nl,
            email=self.email_1,
        )
        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=self.user,
            ).exists()
        )
        self.assertIsNone(subscriber.user)
        self.assertIsNone(subscriber.subscribed)

        # Confirm subscription before activate
        subscriber.subscribe()
        self.assertIsNone(subscriber.user)
        self.assertIsNotNone(subscriber.subscribed)

        # Activate user
        self.user.is_active = True
        self.user.save()
        activate_newsletter_subscription(self.user)
        subscriber.refresh_from_db()

        self.assertIsNotNone(subscriber.user)
        self.assertIsNotNone(subscriber.subscribed)

    def test_newsletter_user_email_changed_user_sub_exists(self):
        """
        for all subs with new email:
            - if user sub exists: delete email sub
            - else: make user sub
        """
        Subscriber.objects.create(
            newsletter=self.nl, user=self.user, subscribed=timezone.now()
        )
        Subscriber.objects.create(
            newsletter=self.nl, email=self.email_2, subscribed=timezone.now()
        )
        self.user.email = self.email_2
        self.user.save()
        user_email_changed(self.user)

        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                email=self.email_2,
            ).exists()
        )
        self.assertTrue(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=self.user,
            ).exists()
        )

    def test_newsletter_user_email_changed_user_sub_not_exists(self):
        """
        for all subs with new email:
            - if user sub exists: delete email sub
            - else: make user sub
        """
        Subscriber.objects.create(
            newsletter=self.nl, email=self.email_2, subscribed=timezone.now()
        )
        self.user.email = self.email_2
        self.user.save()
        user_email_changed(self.user)

        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                email=self.email_2,
            ).exists()
        )
        self.assertTrue(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=self.user,
            ).exists()
        )

    def test_newsletter_user_merge_user_sub_exists(self):
        """
        for all subs with old user:
            - if user sub exists: delete old user sub
            - else: change old user sub to new user
        """
        user_1 = self.user
        user_2 = UserFactory.create(email=self.email_2)
        Subscriber.objects.create(
            newsletter=self.nl, user=user_1, subscribed=timezone.now()
        )
        Subscriber.objects.create(
            newsletter=self.nl, user=user_2, subscribed=timezone.now()
        )
        merge_user(User, old_user=user_1, new_user=user_2)

        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=user_1,
            ).exists()
        )
        self.assertTrue(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=user_2,
            ).exists()
        )

    def test_newsletter_user_merge_user_sub_not_exists(self):
        """
        for all subs with old user:
            - if user sub exists: delete old user sub
            - else: change old user sub to new user
        """
        user_1 = self.user
        user_2 = UserFactory.create(email=self.email_2)
        Subscriber.objects.create(
            newsletter=self.nl, user=user_1, subscribed=timezone.now()
        )
        merge_user(User, old_user=user_1, new_user=user_2)

        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=user_1,
            ).exists()
        )
        self.assertTrue(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=user_2,
            ).exists()
        )

    def test_newsletter_cancel_user(self):
        user = self.user
        Subscriber.objects.create(
            newsletter=self.nl, user=user, subscribed=timezone.now()
        )
        cancel_user(User, user=user)

        self.assertFalse(
            Subscriber.objects.filter(
                newsletter=self.nl,
                user=user,
            ).exists()
        )
        self.assertTrue(
            Subscriber.objects.filter(
                newsletter=self.nl,
                email=user.email,
            ).exists()
        )

    def test_newsletter_bounce(self):
        Subscriber.objects.create(
            newsletter=self.nl, email=self.email_1, subscribed=timezone.now()
        )

        class FakeBounce:
            email = self.email_1
            user = None

        handle_bounce(None, FakeBounce, should_deactivate=True)

        self.assertTrue(
            Subscriber.objects.filter(
                newsletter=self.nl,
                email=self.email_1,
                unsubscribed__isnull=False,
                unsubscribe_method="bounced",
            ).exists()
        )

    def test_newsletter_unsubscribed_via_email(self):
        response = self.client.post(
            reverse("newsletter_subscribe_request"),
            data={"email": self.email_1, "reference": "test"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        unsubscribe_header = email.extra_headers["List-Unsubscribe"]
        subject = unsubscribe_header.split("subject=")[1][:-1]
        reference = subject.split("-", 1)[1]

        handle_unsubscribe(None, self.email_1, reference)

        self.assertTrue(
            Subscriber.objects.filter(
                newsletter=self.nl,
                email=self.email_1,
                unsubscribed__isnull=False,
                unsubscribe_method="unsubscribe-mail",
            ).exists()
        )

    def test_newsletter_unsubscribe_link(self):
        subscriber = Subscriber.objects.create(
            newsletter=self.nl, email=self.email_1, subscribed=timezone.now()
        )
        unsub_url = subscriber.get_unsubscribe_url()
        unsub_path = urlparse(unsub_url).path
        response = self.client.get(unsub_path)
        self.assertEqual(response.status_code, 200)

        # Should auto-post
        response = self.client.post(unsub_path)
        self.assertEqual(response.status_code, 302)

        subscriber.refresh_from_db()

        self.assertIsNone(subscriber.subscribed)
        self.assertIsNotNone(subscriber.unsubscribed)
        self.assertIsNotNone(subscriber.unsubscribe_method, "unsubscribe-link")

    def test_newsletter_unsubscribe_link_reference(self):
        subscriber = Subscriber.objects.create(
            newsletter=self.nl, email=self.email_1, subscribed=timezone.now()
        )
        unsub_url = subscriber.get_unsubscribe_url(reference="unsubref")
        response = self.client.get(unsub_url)
        self.assertEqual(response.status_code, 200)

        post_url = response.context["form_action"]
        response = self.client.post(post_url)
        self.assertEqual(response.status_code, 302)

        subscriber.refresh_from_db()

        self.assertIsNone(subscriber.subscribed)
        self.assertIsNotNone(subscriber.unsubscribed)
        self.assertIsNotNone(subscriber.unsubscribe_method, "unsubscribe-link")
        self.assertIsNotNone(subscriber.unsubscribe_reference, "unsubref")

    def test_subscribe_from_follow(self):
        class FakeFollower:
            email = self.email_2
            confirmed = True
            user = None
            content_object_id = 42
            context = {"newsletter": True}

            class _meta:
                label_lower = "foirequest"

        subscribe_follower(FakeFollower)

        self.assertTrue(
            Subscriber.objects.filter(
                newsletter=self.nl,
                email=self.email_2,
                subscribed__isnull=False,
                reference="follow_extra",
                keyword="foirequest:42",
            ).exists()
        )


@pytest.mark.django_db
def test_activation_delay(mailoutbox):
    nl = Newsletter.objects.create(title="Newsletter", slug="newsletter")
    subscribe(nl, "test@example.com")
    assert len(mailoutbox) == 1
    subscribe(nl, "test@example.com")
    assert len(mailoutbox) == 1


@pytest.mark.django_db
def test_already_delay(mailoutbox):
    nl = Newsletter.objects.create(title="Newsletter", slug="newsletter")
    Subscriber.objects.create(
        newsletter=nl, email="test@example.com", subscribed=timezone.now()
    )
    subscribe(nl, "test@example.com")
    assert len(mailoutbox) == 1
    subscribe(nl, "test@example.com")
    assert len(mailoutbox) == 1
