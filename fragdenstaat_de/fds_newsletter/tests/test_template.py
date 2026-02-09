from io import StringIO

from django.utils import timezone

import pytest

from fragdenstaat_de.fds_mailing.models import EmailTemplate
from fragdenstaat_de.fds_newsletter.utils import subscribe

from ..models import Newsletter, Subscriber
from ..utils import import_csv


@pytest.fixture
def templated_newsletter():
    confirm_template = EmailTemplate.objects.create(
        name="confirm template",
        subject="Confirm",
        active=True,
        text="Hello!\n\n{{ action_url }}\n\nBye!",
    )
    already_template = EmailTemplate.objects.create(
        name="already template",
        subject="Already",
        active=True,
        text="You got it!",
    )
    batch_template = EmailTemplate.objects.create(
        name="batch template",
        subject="Batch",
        active=True,
        text="Please click {{ action_url }}",
    )

    return Newsletter.objects.create(
        title="Test",
        slug="test",
        sender_email="test@example.com",
        sender_name="Test Sender",
        confirm_template=confirm_template,
        confirm_batch_template=batch_template,
        already_subscribed_template=already_template,
    )


@pytest.mark.django_db
def test_subscribe_confirm_template(templated_newsletter, mailoutbox):
    subscribe(templated_newsletter, "email@example.com")
    sub = templated_newsletter.subscribers.all()[0]
    assert len(mailoutbox) == 1
    m = mailoutbox[0]
    assert m.subject == "Confirm"
    assert m.from_email == '"Test Sender" <test@example.com>'
    assert m.body.startswith("Hello!\n\n")
    assert sub.get_subscribe_url() in m.body


@pytest.mark.django_db
def test_subscribe_already_template(templated_newsletter, mailoutbox):
    sub = Subscriber.objects.create(
        newsletter=templated_newsletter,
        email="email@example.com",
        subscribed=timezone.now(),
    )

    subscribe(templated_newsletter, sub.email)
    assert len(mailoutbox) == 1
    m = mailoutbox[0]
    assert m.subject == "Already"
    assert m.from_email == '"Test Sender" <test@example.com>'
    assert m.body.startswith("You got it!")


@pytest.mark.django_db
def test_import_csv(mailoutbox, templated_newsletter):
    csv_data = (
        "email,name,tags\ntest1@example.com,Test1,\ntest2@example.com,Test2,testtag"
    )
    csv_file = StringIO(csv_data)
    sub1 = Subscriber.objects.create(
        newsletter=templated_newsletter,
        email="test1@example.com",
        subscribed=timezone.now(),
        reference="original",
    )
    import_csv(
        csv_file, templated_newsletter, reference="import-1", tags=["import-tag"]
    )

    sub1.refresh_from_db()
    assert set(sub1.tags.all().values_list("name", flat=True)) == {"import-tag"}
    assert sub1.reference == "original"

    sub2 = Subscriber.objects.get(
        newsletter=templated_newsletter, email="test2@example.com"
    )
    assert sub2.subscribed is None
    assert set(sub2.tags.all().values_list("name", flat=True)) == {
        "import-tag",
        "testtag",
    }
    assert sub2.reference == "import-1"
    assert len(mailoutbox) == 1
    m = mailoutbox[0]
    assert m.to[0] == sub2.email
    assert m.subject == "Batch"
    assert m.body.startswith("Please click ")
    assert sub2.get_subscribe_url() in m.body
