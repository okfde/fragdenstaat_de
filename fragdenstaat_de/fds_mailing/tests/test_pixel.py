from urllib.parse import urlparse

from django.conf import settings

import pytest

from fragdenstaat_de.fds_mailing.utils import (
    LowerCaseSigner,
    SignedPixelPath,
    generate_random_unique_pixel_url,
    verify_random_unique_pixel_url,
)


@pytest.mark.django_db
def test_generate_random_unique_pixel_url(settings):
    """Test the generation of a random unique pixel URL."""
    settings.NEWSLETTER_PIXEL_ORIGIN = "https://example.com"
    mailing_id = 123
    namespace = "mailing"

    url = generate_random_unique_pixel_url(mailing_id, namespace=namespace)

    assert url.startswith(
        f"{settings.NEWSLETTER_PIXEL_ORIGIN}/{namespace}/{mailing_id}/"
    )
    assert url.endswith(".gif")
    parsed_url = urlparse(url)

    assert len(parsed_url.path.split("/")) == 5  # Ensure the URL structure is correct


@pytest.mark.django_db
def test_verify_random_unique_pixel_url_valid(settings):
    """Test verifying a valid random unique pixel URL."""
    settings.NEWSLETTER_PIXEL_ORIGIN = "https://example.com"
    mailing_id = 123
    namespace = "mailing"

    url = generate_random_unique_pixel_url(mailing_id, namespace=namespace)
    result = verify_random_unique_pixel_url(url)
    assert isinstance(result, SignedPixelPath)

    assert result is not None
    assert result.namespace == namespace
    assert result.mailing_id == mailing_id
    assert result.valid is True


@pytest.mark.django_db
def test_verify_random_unique_pixel_url_invalid_signature(settings):
    """Test verifying a pixel URL with an invalid signature."""
    settings.NEWSLETTER_PIXEL_ORIGIN = "https://example.com"
    mailing_id = 123
    namespace = "mailing"

    url = generate_random_unique_pixel_url(mailing_id, namespace=namespace)
    # Tamper with the URL to invalidate the signature
    tampered_url = url.replace("mailing", "tampered")

    result = verify_random_unique_pixel_url(tampered_url)

    assert result is not None
    assert result.namespace == "tampered"
    assert result.mailing_id == mailing_id
    assert result.valid is False


@pytest.mark.django_db
def test_verify_random_unique_pixel_url_invalid_format():
    """Test verifying a pixel URL with an invalid format."""
    invalid_url = "https://example.com/invalid/url/format"

    result = verify_random_unique_pixel_url(invalid_url)

    assert result is None


@pytest.mark.django_db
def test_verify_random_unique_pixel_url_missing_gif_extension():
    """Test verifying a pixel URL missing the .gif extension."""
    settings.NEWSLETTER_PIXEL_ORIGIN = "https://example.com"
    mailing_id = 123
    namespace = "mailing"

    signer = LowerCaseSigner()
    random = "randomstring"
    path = f"{namespace}/{mailing_id}/{random}"
    signature = signer.signature(path)
    invalid_url = f"{settings.NEWSLETTER_PIXEL_ORIGIN}/{path}/{signature}"

    result = verify_random_unique_pixel_url(invalid_url)

    assert result is None
