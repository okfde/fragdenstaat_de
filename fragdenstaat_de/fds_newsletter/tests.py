import re
from urllib.parse import urlparse

from django.test import TestCase
from django.conf import settings
from django.urls import reverse
from django.core import mail
from django.test.utils import override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from froide.foirequest.tests.factories import UserFactory

from .listeners import (
    activate_newsletter_subscription,
    user_email_changed,
    merge_user,
    cancel_user,
    handle_bounce, handle_unsubscribe
)
from .models import Newsletter, Subscriber

User = get_user_model()

SPAM_DISABLED_CONFIG = dict(settings.FROIDE_CONFIG)
SPAM_DISABLED_CONFIG['spam_protection'] = False


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
    def setUp(self):
        self.nl = Newsletter.objects.get(
            slug=settings.DEFAULT_NEWSLETTER
        )
        # create(
        #     title='Newsletter', slug=settings.DEFAULT_NEWSLETTER,
        #     visible=True, sender_email='info@fragdenstaat.de',
        #     sender_name='FragDenStaat'
        # )
        self.email_1 = 'one@example.com'
        self.email_2 = 'two@example.com'

    def test_default_newsletter_subscription(self):
        mail.outbox = []
        response = self.client.post(
            reverse('newsletter_subscribe_request'),
            data={'email': self.email_1, 'reference': 'test'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Subscriber.objects.filter(
            newsletter=self.nl, email=self.email_1,
            subscribed=None, unsubscribed=None).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        match = re.search(r'://[^/]+(/.*)', message.body)
        response = self.client.get(match.group(1))
        self.assertEqual(response.status_code, 302)
        subscriber = Subscriber.objects.get(
            newsletter=self.nl, email=self.email_1,
            subscribed__isnull=False
        )
        self.assertEqual(subscriber.reference, 'test')

    def test_newsletter_subscription_existing_user_with_email(self):
        user = UserFactory.create(email=self.email_1)
        response = self.client.post(
            reverse('newsletter_subscribe_request'),
            data={'email': self.email_1, 'reference': 'test'}
        )
        self.assertEqual(response.status_code, 302)

        subscriber = Subscriber.objects.get(
            newsletter=self.nl, email=self.email_1,
            subscribed=None, unsubscribed=None)
        self.assertEqual(len(mail.outbox), 1)
        # confirm subscription
        subscriber.subscribe()
        subscriber.refresh_from_db()
        self.assertIsNotNone(subscriber.subscribed)
        self.assertEqual(subscriber.user, user)
        self.assertIsNone(subscriber.email)

    def test_newsletter_subscription_existing_user_subscriber_with_email(self):
        user = UserFactory.create(email=self.email_1)
        user_subscriber = Subscriber.objects.create(
            newsletter=self.nl,
            user=user
        )
        response = self.client.post(
            reverse('newsletter_subscribe_request'),
            data={'email': self.email_1, 'reference': 'test'}
        )
        self.assertEqual(response.status_code, 302)
        subscriber = Subscriber.objects.get(
            newsletter=self.nl, email=self.email_1,
            subscribed=None, unsubscribed=None)
        self.assertEqual(len(mail.outbox), 1)
        subscriber.subscribe()
        new_subscriber = Subscriber.objects.get(
            newsletter=self.nl, user=user,
            subscribed__isnull=False
        )
        self.assertIsNone(subscriber.id)
        self.assertEqual(new_subscriber, user_subscriber)

    def test_newsletter_subscription_logged_in_same_email(self):
        user = UserFactory.create(email=self.email_1)
        self.client.force_login(user)
        response = self.client.post(
            reverse('newsletter_subscribe_request'),
            data={'email': self.email_1, 'reference': 'test'}
        )
        self.assertEqual(response.status_code, 302)

        subscriber = Subscriber.objects.get(
            newsletter=self.nl, user=user,
        )
        self.assertIsNotNone(subscriber.subscribed)
        self.assertEqual(len(mail.outbox), 0)

    def test_newsletter_subscription_logged_in_different_email(self):
        user = UserFactory.create(email=self.email_1)
        self.client.force_login(user)
        self.client.post(
            reverse('newsletter_subscribe_request'),
            data={'email': self.email_2, 'reference': 'test'}
        )
        self.assertFalse(Subscriber.objects.filter(
            newsletter=self.nl, user=user,
        ).exists())
        self.assertEqual(len(mail.outbox), 1)
        subscriber = Subscriber.objects.get(
            newsletter=self.nl, email=self.email_2,
        )
        self.assertIsNone(subscriber.subscribed)
        subscriber.subscribe()
        self.assertIsNotNone(subscriber.subscribed)
        self.assertIsNone(subscriber.user)

    def test_newsletter_email_subscription_activate_account(self):
        user = UserFactory.create(email=self.email_1, is_active=False)
        response = self.client.post(
            reverse('newsletter_subscribe_request'),
            data={'email': self.email_1, 'reference': 'test'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Subscriber.objects.filter(
            newsletter=self.nl, user=user,
        ).exists())
        self.assertEqual(len(mail.outbox), 1)
        subscriber = Subscriber.objects.get(
            newsletter=self.nl, email=self.email_1,
        )
        # Activate user before confirming subscription
        user.is_active = True
        user.save()
        activate_newsletter_subscription(user)

        self.assertFalse(Subscriber.objects.filter(
            newsletter=self.nl, user=user,
        ).exists())
        subscriber.refresh_from_db()
        self.assertIsNone(subscriber.user)
        self.assertIsNone(subscriber.subscribed)

        subscriber.subscribe()
        self.assertIsNotNone(subscriber.user)
        self.assertIsNotNone(subscriber.subscribed)

    def test_newsletter_email_subscription_activate_account_later(self):
        user = UserFactory.create(email=self.email_1, is_active=False)
        response = self.client.post(
            reverse('newsletter_subscribe_request'),
            data={'email': self.email_1, 'reference': 'test'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Subscriber.objects.filter(
            newsletter=self.nl, user=user,
        ).exists())
        self.assertEqual(len(mail.outbox), 1)
        subscriber = Subscriber.objects.get(
            newsletter=self.nl, email=self.email_1,
        )
        self.assertFalse(Subscriber.objects.filter(
            newsletter=self.nl, user=user,
        ).exists())
        self.assertIsNone(subscriber.user)
        self.assertIsNone(subscriber.subscribed)

        # Confirm subscription before activate
        subscriber.subscribe()
        self.assertIsNone(subscriber.user)
        self.assertIsNotNone(subscriber.subscribed)

        # Activate user
        user.is_active = True
        user.save()
        activate_newsletter_subscription(user)
        subscriber.refresh_from_db()

        self.assertIsNotNone(subscriber.user)
        self.assertIsNotNone(subscriber.subscribed)

    def test_newsletter_user_email_changed_user_sub_exists(self):
        '''
        for all subs with new email:
            - if user sub exists: delete email sub
            - else: make user sub
        '''
        user = UserFactory.create(email=self.email_1)
        Subscriber.objects.create(
            newsletter=self.nl, user=user,
            subscribed=timezone.now()
        )
        Subscriber.objects.create(
            newsletter=self.nl, email=self.email_2,
            subscribed=timezone.now()
        )
        user.email = self.email_2
        user.save()
        user_email_changed(user)

        self.assertFalse(Subscriber.objects.filter(
            newsletter=self.nl, email=self.email_2,
        ).exists())
        self.assertTrue(Subscriber.objects.filter(
            newsletter=self.nl, user=user,
        ).exists())

    def test_newsletter_user_email_changed_user_sub_not_exists(self):
        '''
        for all subs with new email:
            - if user sub exists: delete email sub
            - else: make user sub
        '''
        user = UserFactory.create(email=self.email_1)
        Subscriber.objects.create(
            newsletter=self.nl, email=self.email_2,
            subscribed=timezone.now()
        )
        user.email = self.email_2
        user.save()
        user_email_changed(user)

        self.assertFalse(Subscriber.objects.filter(
            newsletter=self.nl, email=self.email_2,
        ).exists())
        self.assertTrue(Subscriber.objects.filter(
            newsletter=self.nl, user=user,
        ).exists())

    def test_newsletter_user_merge_user_sub_exists(self):
        '''
        for all subs with old user:
            - if user sub exists: delete old user sub
            - else: change old user sub to new user
        '''
        user_1 = UserFactory.create(email=self.email_1)
        user_2 = UserFactory.create(email=self.email_2)
        Subscriber.objects.create(
            newsletter=self.nl, user=user_1,
            subscribed=timezone.now()
        )
        Subscriber.objects.create(
            newsletter=self.nl, user=user_2,
            subscribed=timezone.now()
        )
        merge_user(User, old_user=user_1, new_user=user_2)

        self.assertFalse(Subscriber.objects.filter(
            newsletter=self.nl, user=user_1,
        ).exists())
        self.assertTrue(Subscriber.objects.filter(
            newsletter=self.nl, user=user_2,
        ).exists())

    def test_newsletter_user_merge_user_sub_not_exists(self):
        '''
        for all subs with old user:
            - if user sub exists: delete old user sub
            - else: change old user sub to new user
        '''
        user_1 = UserFactory.create(email=self.email_1)
        user_2 = UserFactory.create(email=self.email_2)
        Subscriber.objects.create(
            newsletter=self.nl, user=user_1,
            subscribed=timezone.now()
        )
        merge_user(User, old_user=user_1, new_user=user_2)

        self.assertFalse(Subscriber.objects.filter(
            newsletter=self.nl, user=user_1,
        ).exists())
        self.assertTrue(Subscriber.objects.filter(
            newsletter=self.nl, user=user_2,
        ).exists())

    def test_newsletter_cancel_user(self):
        user = UserFactory.create(email=self.email_1)
        Subscriber.objects.create(
            newsletter=self.nl, user=user,
            subscribed=timezone.now()
        )
        cancel_user(User, user=user)

        self.assertFalse(Subscriber.objects.filter(
            newsletter=self.nl, user=user,
        ).exists())
        self.assertTrue(Subscriber.objects.filter(
            newsletter=self.nl, email=user.email,
        ).exists())

    def test_newsletter_bounce(self):
        Subscriber.objects.create(
            newsletter=self.nl, email=self.email_1,
            subscribed=timezone.now()
        )

        class FakeBounce:
            email = self.email_1
            user = None

        handle_bounce(None, FakeBounce, should_deactivate=True)

        self.assertTrue(Subscriber.objects.filter(
            newsletter=self.nl, email=self.email_1,
            unsubscribed__isnull=False,
            unsubscribe_method='bounced'
        ).exists())

    def test_newsletter_unsubscribed_via_email(self):
        response = self.client.post(
            reverse('newsletter_subscribe_request'),
            data={'email': self.email_1, 'reference': 'test'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        unsubscribe_header = email.extra_headers['List-Unsubscribe']
        subject = unsubscribe_header.split('subject=')[1][:-1]
        reference = subject.split('-', 1)[1]

        handle_unsubscribe(None, self.email_1, reference)

        self.assertTrue(Subscriber.objects.filter(
            newsletter=self.nl, email=self.email_1,
            unsubscribed__isnull=False,
            unsubscribe_method='unsubscribe-mail'
        ).exists())

    def test_newsletter_unsubscribe_link(self):
        subscriber = Subscriber.objects.create(
            newsletter=self.nl, email=self.email_1,
            subscribed=timezone.now()
        )
        unsub_url = subscriber.get_unsubscribe_url()
        unsub_path = urlparse(unsub_url).path
        response = self.client.get(unsub_path)
        self.assertEqual(response.status_code, 302)

        subscriber.refresh_from_db()

        self.assertIsNone(subscriber.subscribed)
        self.assertIsNotNone(subscriber.unsubscribed)
        self.assertIsNotNone(subscriber.unsubscribe_method, 'unsubscribe-link')
