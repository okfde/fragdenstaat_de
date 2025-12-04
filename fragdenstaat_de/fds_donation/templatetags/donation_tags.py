from decimal import Decimal

from django.template import Library
from django.utils.safestring import mark_safe

import qrcode
import qrcode.image.svg

from ..forms import SubscriptionCancelFeedbackForm

register = Library()


@register.simple_tag
def get_subscription_cancel_feedback_form():
    return SubscriptionCancelFeedbackForm()


@register.simple_tag
def sepa_qrcode(
    recipient: str, iban: str, bic: str, amount: Decimal, reference: str
) -> str:
    data = f"""BCD
001
1
SCT
{bic}
{recipient}
{iban}
EUR{amount}


{reference}"""
    img = (
        qrcode.make(data, image_factory=qrcode.image.svg.SvgImage, border=0)
        .to_string()
        .decode("utf-8")
    )
    return mark_safe(img)
