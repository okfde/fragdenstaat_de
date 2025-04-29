from django.conf import settings
from django.core import mail
from django.utils import timezone

import pytest
from cms.api import add_plugin

from fragdenstaat_de.fds_newsletter.listeners import handle_unsubscribe
from fragdenstaat_de.fds_newsletter.models import Newsletter, Subscriber

from ..models import EmailTemplate, Mailing


@pytest.fixture
def newsletter():
    nl = Newsletter.objects.create(
        title="Test newsletter",
        slug="test-newsletter",
        description="Test description",
    )
    _sub_1 = Subscriber.objects.create(
        email="subscribed@example.org",
        newsletter=nl,
        subscribed=timezone.now(),
    )
    _sub_2 = Subscriber.objects.create(
        email="unsubscribed@example.org",
        newsletter=nl,
        unsubscribed=timezone.now(),
    )
    return nl


@pytest.fixture
def email_template():
    et = EmailTemplate.objects.create(
        name="test", subject="Test subject", preheader="Test preheader", template="mjml"
    )
    body_plugin = add_plugin(et.email_body, "EmailBodyPlugin", "de")
    add_plugin(
        et.email_body,
        "TextPlugin",
        "de",
        body='<p>Content <a href="{}/link/"</p>'.format(settings.SITE_URL),
        position="first-child",
        target=body_plugin,
    )
    return et


@pytest.fixture
def mailing(email_template, newsletter):
    return Mailing.objects.create(
        name="Test mailing",
        email_template=email_template,
        newsletter=newsletter,
        sending_date=None,
        tracking=True,
        ready=True,
        submitted=True,
        sent=False,
        sending=False,
    )


@pytest.mark.django_db
def test_mailing_render(mailing):
    assert mailing.get_subscribers().count() == 1
    mailing.auto_populate()
    assert mailing.recipients.count() == 1

    mailing_message = mailing.recipients.first()
    context = mailing_message.get_email_context()
    subscribers = mailing.newsletter.subscribers.all()
    assert subscribers.count() == 2
    subscribers = subscribers.filter(subscribed__isnull=False)
    subscriber = subscribers.first()
    assert subscriber.email == mailing_message.email
    assert subscriber == mailing_message.subscriber
    assert context["subscriber"] == subscriber
    assert context["unsubscribe_reference"] == "newsletter-{}-{}".format(
        subscriber.id, mailing.mailing_ident
    )
    assert mailing.mailing_ident in context["unsubscribe_url"]
    assert context["unsubscribe_url"] == subscriber.get_unsubscribe_url(
        reference=mailing.mailing_ident
    )

    email_content = mailing.get_email_content(context)
    assert email_content.subject == mailing.email_template.subject
    assert (
        "{}/link/?pk_campaign={}".format(settings.SITE_URL, mailing.mailing_ident)
        in email_content.text
    )
    assert (
        "{}/link/?pk_campaign={}".format(settings.SITE_URL, mailing.mailing_ident)
        in email_content.html
    )
    assert '<img src="{}'.format(settings.NEWSLETTER_PIXEL_ORIGIN) in email_content.html

    mail.outbox = []
    mailing.sending = True
    mailing_message.send_message()

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    unsubscribe_header = email.extra_headers["List-Unsubscribe"]
    subject = unsubscribe_header.split("subject=")[1][:-1]
    reference = subject.split("-", 1)[1]
    assert reference == context["unsubscribe_reference"]
    handle_unsubscribe(None, email.to[0], reference)
    subscriber.refresh_from_db()
    assert subscriber.unsubscribed is not None
    assert subscriber.unsubscribe_method == "unsubscribe-mail"
    assert subscriber.unsubscribe_reference == mailing.mailing_ident
