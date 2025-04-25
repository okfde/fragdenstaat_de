import io
from urllib.parse import urlparse

from django.conf import settings

import pytest

from fragdenstaat_de.fds_mailing.models import Mailing
from fragdenstaat_de.fds_mailing.pixel_log import (
    generate_random_unique_pixel_url,
    parse_pixel_path,
    validate_pixel_path_signature,
)
from fragdenstaat_de.fds_mailing.pixel_log_parsing import (
    PixelLogParser,
    PixelProcessor,
    read_pixel_log,
)
from fragdenstaat_de.fds_mailing.utils import LowerCaseSigner


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
def test_validate_random_unique_pixel_url_valid(settings):
    """Test verifying a valid random unique pixel URL."""
    settings.NEWSLETTER_PIXEL_ORIGIN = "https://example.com"
    mailing_id = 123
    namespace = "mailing"

    url = generate_random_unique_pixel_url(mailing_id, namespace=namespace)
    pixel_path = parse_pixel_path(url)
    assert validate_pixel_path_signature(pixel_path)

    assert pixel_path.namespace == namespace
    assert pixel_path.mailing_id == mailing_id


@pytest.mark.django_db
def test_verify_random_unique_pixel_url_invalid_signature(settings):
    """Test verifying a pixel URL with an invalid signature."""
    settings.NEWSLETTER_PIXEL_ORIGIN = "https://example.com"
    mailing_id = 123
    namespace = "mailing"

    url = generate_random_unique_pixel_url(mailing_id, namespace=namespace)
    # Tamper with the URL to invalidate the signature
    tampered_url = url.replace("mailing", "tampered")

    pixelpath = parse_pixel_path(tampered_url)
    assert not validate_pixel_path_signature(pixelpath)


@pytest.mark.django_db
def test_verify_random_unique_pixel_url_invalid_format():
    """Test verifying a pixel URL with an invalid format."""
    invalid_url = "https://example.com/invalid/url/format"

    result = parse_pixel_path(invalid_url)

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

    result = parse_pixel_path(invalid_url)

    assert result is None


SAMPLE_LOG = """
24/Apr/2025:11:13:45 +0200|GET / HTTP/2.0
24/Apr/2025:11:13:45 +0200|GET /favicon.ico HTTP/2.0
24/Apr/2025:11:14:07 +0200|HEAD / HTTP/1.1
24/Apr/2025:11:15:07 +0200|HEAD / HTTP/1.1
24/Apr/2025:11:16:07 +0200|HEAD / HTTP/1.1
24/Apr/2025:11:23:14 +0200|GET /test.gif HTTP/2.0
24/Apr/2025:11:37:37 +0200|GET /mailing/511/6smqsgqq1674/test.gif HTTP/2.0
24/Apr/2025:14:12:42 +0200|GET /.env HTTP/1.1"""


def test_parse_pixel_log():
    parser = PixelLogParser(io.StringIO(SAMPLE_LOG))

    result = list(parser)

    assert len(result) == 2
    first = result[0]
    assert first.timestamp.second == 14
    assert first.path == "/test.gif"
    second = result[1]
    assert second.timestamp.second == 37
    assert second.path == "/mailing/511/6smqsgqq1674/test.gif"


def test_validate_pixel_log():
    url = generate_random_unique_pixel_url(123, namespace="mailing")
    path = urlparse(url).path
    log_lines = "\n".join(
        [SAMPLE_LOG, f"24/Apr/2025:14:12:43 +0200|GET {path} HTTP/2.0"]
    )

    parser = PixelLogParser(io.StringIO(log_lines))
    reader = read_pixel_log(parser)
    result = list(reader)

    assert len(result) == 1
    pixel = result[0]
    assert pixel.mailing_id == 123
    assert pixel.namespace == "mailing"
    assert pixel.timestamp.second == 43


@pytest.mark.django_db
def test_processing_pixel_log():
    mailing = Mailing.objects.create(
        open_count=0,
        tracking=True,
        ready=True,
        submitted=True,
        sending=True,
    )
    url = generate_random_unique_pixel_url(mailing.id, namespace="mailing")
    path = urlparse(url).path
    parts = path.split("/")
    log_lines = "\n".join(
        [
            SAMPLE_LOG,
            f"24/Apr/2025:14:12:43 +0200|GET {path} HTTP/2.0",
            f"24/Apr/2025:14:12:44 +0200|GET {path} HTTP/2.0",  # Same pixel twice
        ]
    )

    parser = PixelLogParser(io.StringIO(log_lines))
    reader = read_pixel_log(parser)
    processor = PixelProcessor(reader)
    processor.run()

    mailing.refresh_from_db()

    assert processor.mailings[mailing.id] == mailing
    assert processor.token_set[mailing.id] == {parts[3]}
    assert processor.open_count[mailing.id] == 1

    assert mailing.open_count == 1
    assert mailing.open_log_timestamp is not None
    assert mailing.open_log_timestamp.second == 44

    # Run again to check that the pixel is not counted again
    parser = PixelLogParser(io.StringIO(log_lines))
    reader = read_pixel_log(parser)
    processor = PixelProcessor(reader)
    processor.run()
    mailing.refresh_from_db()

    assert mailing.open_count == 1
    assert mailing.open_log_timestamp is not None
    assert mailing.open_log_timestamp.second == 44

    # Run again with higher timestamp and its counted
    # as we are not aware of previous runs
    log_lines = f"24/Apr/2025:14:12:45 +0200|GET {path} HTTP/2.0"

    parser = PixelLogParser(io.StringIO(log_lines))
    reader = read_pixel_log(parser)
    processor = PixelProcessor(reader)
    processor.run()
    mailing.refresh_from_db()

    assert mailing.open_count == 2
    assert mailing.open_log_timestamp is not None
    assert mailing.open_log_timestamp.second == 45
