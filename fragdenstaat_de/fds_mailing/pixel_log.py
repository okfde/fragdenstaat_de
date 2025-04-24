from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from django.conf import settings
from django.core.signing import BadSignature
from django.utils.crypto import get_random_string

from .utils import LowerCaseSigner


def generate_random_unique_pixel_url(mailing_id: int, namespace="mailing"):
    random = get_random_string(12, allowed_chars="abcdefghijklmnopqrstuvwxyz0123456789")
    path = f"{namespace}/{mailing_id}/{random}"
    signer = LowerCaseSigner()
    signature = signer.signature(path)
    return f"{settings.NEWSLETTER_PIXEL_ORIGIN}/{path}/{signature}.gif"


@dataclass(frozen=True)
class PixelPath:
    namespace: str
    mailing_id: int
    token: str
    signature: str


def parse_pixel_path(url_string: str) -> Optional[PixelPath]:
    url = urlparse(url_string)
    if url.netloc != "" and not settings.NEWSLETTER_PIXEL_ORIGIN.endswith(url.netloc):
        # Wrong domain
        return None
    path = url.path
    path_parts = [x for x in path.split("/") if x]
    if len(path_parts) != 4:
        return None
    namespace, mailing_id, token, signature_filename = path_parts
    if not signature_filename.endswith(".gif"):
        return None
    try:
        mailing_id = int(mailing_id)
    except ValueError:
        # Invalid mailing ID
        return None
    signature = signature_filename.replace(".gif", "")
    return PixelPath(namespace, mailing_id, token, signature)


def validate_pixel_path_signature(path: PixelPath) -> bool:
    signer = LowerCaseSigner()
    data = f"{path.namespace}/{path.mailing_id}/{path.token}"
    signed_value = signer.sep.join([data, path.signature])
    try:
        signer.unsign(signed_value)
        return True
    except BadSignature:
        return False
