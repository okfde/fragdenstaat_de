import datetime

import pytest

from froide.helper.email_sending import EmailContent

from ..models import EmailTemplate, Mailing
from ..utils import get_url_tagger


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "Visit https://example.com/page for more info.",
            "Visit https://example.com/page?pk_campaign=campaign123 for more info.",
        ),
        (
            "Check https://example.com/page?existing_param=value&empty_param=",
            "Check https://example.com/page?existing_param=value&empty_param=&pk_campaign=campaign123",
        ),
        (
            "Multiple links: https://example.com/page1 and https://example.com/page2 .",
            "Multiple links: https://example.com/page1?pk_campaign=campaign123 and https://example.com/page2?pk_campaign=campaign123 .",
        ),
        (
            "Existing links: https://example.com/page1/?pk_campaign=campaign456",
            "Existing links: https://example.com/page1/?pk_campaign=campaign456",
        ),
        (
            "No links here, just text.",
            "No links here, just text.",
        ),
    ],
)
def test_get_url_tagger(text, expected, settings):
    """Test the URL tagger function with various inputs."""
    settings.SITE_URL = "https://example.com"
    mailing_campaign = "campaign123"
    tagger = get_url_tagger(mailing_campaign)
    result = tagger(text)
    assert result == expected


def test_get_url_tagger_ignores_external_links(settings):
    """Test that the URL tagger ignores links outside the SITE_URL domain."""
    settings.SITE_URL = "https://example.com"
    text = "Visit https://external.com/page for more info."
    mailing_campaign = "campaign123"

    tagger = get_url_tagger(mailing_campaign)
    result = tagger(text)

    assert result == text  # External links should remain unchanged


def test_get_url_tagger_no_duplicate_campaign(settings):
    """Test that the URL tagger does not add duplicate campaign parameters."""
    settings.SITE_URL = "https://example.com"
    text = "Visit https://example.com/page?pk_campaign=campaign123 for more info."
    mailing_campaign = "campaign123"

    tagger = get_url_tagger(mailing_campaign)
    result = tagger(text)

    assert result == text  # No duplicate campaign parameter should be added


def test_mailing_url_tagging(settings):
    settings.SITE_URL = "https://example.com"

    class FakeEmailTemplate:
        def __init__(self, text):
            self.text = text

        def get_email_content(self, ctx):
            text = self.text.replace("{foo}", ctx["foo"])
            return EmailContent("Subject", text, text)

    email_template = EmailTemplate()
    email_template.get_email_content = FakeEmailTemplate(
        "Hello, visit https://example.com/page for more info and click {foo}."
    ).get_email_content

    sending_date = datetime.datetime(
        2024, 12, 13, 12, 42, 40, tzinfo=datetime.timezone.utc
    )
    mailing = Mailing(id=1, sending_date=sending_date, tracking=True)
    mailing.email_template = email_template

    content = mailing.get_email_content({"foo": "bar"})
    assert content.subject == "Subject"
    assert (
        content.text
        == "Hello, visit https://example.com/page?pk_campaign=mailing-202412131242-1 for more info and click bar."
    )
