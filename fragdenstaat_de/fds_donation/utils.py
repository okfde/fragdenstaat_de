import re
from decimal import ROUND_DOWN, ROUND_UP, Decimal

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import Min
from django.template.defaultfilters import floatformat
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from fragdenstaat_de.fds_newsletter.utils import subscribe_to_newsletter

from .models import Donation, Donor, Recurrence, update_donation_numbers

MERGE_DONOR_FIELDS = [
    "salutation",
    "first_name",
    "last_name",
    "company_name",
    "address",
    "city",
    "postcode",
    "country",
    "email",
    "email_confirmed",
    "identifier",
    "attributes",
    "contact_allowed",
    "receipt",
    "note",
    "invalid",
    "user",
    "subscriber",
]


def sort_donors(donors: list[Donor]):
    return sorted(
        donors,
        key=lambda x: x.first_donation,
        reverse=True,
    )


def first(lis, default="", attr=None):
    if len(lis):
        if attr:
            return getattr(lis[0], attr)
        return lis[0]
    return default


def get_latest_filled(attr: str, default=""):
    def latest_filled(donors):
        return first(
            sort_donors([d for d in donors if getattr(d, attr, "")]),
            default=default,
            attr=attr,
        )

    return latest_filled


def get_latest_known(attr: str):
    def latest_known(donors):
        return first(
            sort_donors(
                [d for d in donors if getattr(d, attr) is not None],
            ),
            default=None,
            attr=attr,
        )

    return latest_known


def get_latest(attr: str):
    def latest(donors):
        return first(
            sort_donors(donors),
            default=None,
            attr=attr,
        )

    return latest


def get_falsiest(attr: str):
    def falsiest(donors):
        return all(getattr(d, attr) for d in donors)

    return falsiest


def string_merge(attr: str):
    def merge(donors):
        return "\n\n".join(getattr(d, attr) for d in donors).strip()

    return merge


def get_latest_by_email(attr: str, default=""):
    def latest_by_email(donors):
        return first(
            sorted(
                [d for d in donors if d.email and d.email_confirmed],
                key=lambda x: x.email_confirmed,
                reverse=True,
            ),
            default=default,
            attr=attr,
        )

    return latest_by_email


def get_user(donors):
    proposed_email = get_latest_by_email("email")(donors)
    matching_email_users = [
        d.user for d in donors if d.user and d.user.email == proposed_email
    ]
    if matching_email_users:
        return matching_email_users[0]
    return first(sort_donors(d for d in donors if d.user), default=None, attr="user")


def merge_dict(attr: str):
    def merge(donors):
        data = {}
        for d in donors:
            d_data = getattr(d, attr)
            if not d_data:
                continue
            d_key = f"{d.id}_{attr}"
            data.setdefault(d_key, {})
            data[d_key].update(d_data)
        return data

    return merge


DONOR_SESSION_KEY = "donor_id"


def subscribe_donor_newsletter(donor, email_confirmed=False):
    result, subscriber = subscribe_to_newsletter(
        settings.DONOR_NEWSLETTER,
        donor.email,
        user=donor.user,
        name=donor.get_full_name(),
        email_confirmed=email_confirmed,
    )
    donor.subscriber = subscriber
    donor.save(update_fields=["subscriber"])


def propose_donor_merge(candidates, fields=None):
    if fields is None:
        fields = MERGE_DONOR_FIELDS

    MERGE_DONOR_DECISIONS = {
        # Take newest confirmed email address
        "email": get_latest_by_email("email"),
        "email_confirmed": get_latest_by_email("email_confirmed", default=None),
        "contact_allowed": get_latest_known("contact_allowed"),
        "receipt": get_latest_known("receipt"),
        "note": string_merge("note"),
        "invalid": get_falsiest("invalid"),
        "user": get_user,
        "attributes": merge_dict("attributes"),
        "subscriber": get_latest_filled("subscriber", default=None),
    }
    merged_donor_data = {}
    for field in fields:
        if field in MERGE_DONOR_DECISIONS:
            merged_donor_data[field] = MERGE_DONOR_DECISIONS[field](candidates)
        else:
            merged_donor_data[field] = get_latest_filled(field)(candidates)

    merged_donor = Donor(**merged_donor_data)
    return merged_donor


def merge_donor_list(donors):
    merged_donor = propose_donor_merge(donors)
    merged_donor.id = donors[0].id
    # Set uuid of first donor on merged donor to keep it
    merged_donor.uuid = donors[0].uuid
    candidates = [merged_donor, *donors[1:]]
    return merge_donors(candidates, merged_donor.id)


def merge_donors(candidates, primary_id, validated_data=None):
    from .services import detect_recurring_on_donor

    # Collect old ids and references

    old_fields = ["id", "uuid", "email", "email_confirmed"]
    old_data = []
    old_addresses = []
    subscriptions = []
    for candidate in candidates:
        if candidate.id == primary_id:
            continue
        old_data.append({f: str(getattr(candidate, f)) for f in old_fields})
        old_addresses.append(candidate.get_full_address())

        for sub in candidate.subscriptions.all():
            subscriptions.append(sub)

    merged_donor = [c for c in candidates if c.id == primary_id][0]

    if validated_data:
        # Set form data on primary
        for key, val in validated_data.items():
            setattr(merged_donor, key, val)

    merged_address = merged_donor.get_full_address()
    for old_address in old_addresses:
        if merged_address != old_address:
            merged_donor.note += "\n\n---\n{old_address}\n---\n\n".format(
                old_address=old_address
            )
            merged_donor.note = merged_donor.note.strip()

    # Add old ids to attributes
    attrs = merged_donor.attributes or {}

    if "old_data" in attrs:
        attrs["old_data"].extend(old_data)
    else:
        attrs["old_data"] = old_data

    merged_donor.attributes = attrs

    # Clear duplicate flag
    merged_donor.duplicate = None

    merged_donor.save()

    # Add other candidates subscriptions
    merged_donor.subscriptions.add(*subscriptions)

    # Merge tags
    for candidate in candidates:
        if candidate.id == primary_id:
            continue
        merged_donor.tags.add(*candidate.tags.all())

    old_donor_ids = [c.id for c in candidates if c.id != primary_id]
    # Transfer donations
    Donation.objects.filter(donor_id__in=old_donor_ids).update(donor=merged_donor)
    # Transfer recurrences
    Recurrence.objects.filter(donor_id__in=old_donor_ids).update(donor=merged_donor)
    # Delete old donors
    Donor.objects.filter(id__in=old_donor_ids).delete()

    # Recalculate stored aggregates
    aggs = Donation.objects.filter(donor=merged_donor).aggregate(
        first_donation=Min("timestamp"),
    )
    merged_donor.first_donation = aggs["first_donation"]
    merged_donor.save()

    update_donation_numbers(merged_donor.id)

    detect_recurring_on_donor(merged_donor)

    return merged_donor


def get_donation_pivot_data_and_config(queryset):
    keys = [
        "donor_id",
        "amount",
        "timestamp",
        "method",
        "reference",
        "keyword",
        "purpose",
        "recurring",
        "first_recurring",
    ]
    data = [[getattr(x, k) for k in keys] for x in queryset]
    config = {"extra": {"vals": ["amount"]}, "dateColumn": "timestamp"}
    final_data = [keys]
    final_data.extend(data)
    return final_data, config


def selective_title_case(val):
    parts = val.split(" ")
    # Silly heuristic to avoid title casing von, van, etc.
    parts = [p.title() if len(p) > 3 else p for p in parts]
    return " ".join(parts)


def make_donor_fields_title_case(donor):
    fields = ("first_name", "last_name", "address", "city")
    updated_fields = set()
    for field in fields:
        val = getattr(donor, field)
        new_val = selective_title_case(val)
        if val != new_val:
            updated_fields.add(field)
            setattr(donor, field, new_val)
    return updated_fields


NO_DOT_ADRESS_REGEX = re.compile(r"([sS]tr) ")


def fix_adress(donor):
    new_address = NO_DOT_ADRESS_REGEX.sub(r"\1. ", donor.address)
    if new_address != donor.address:
        donor.address = new_address
        return {"address"}
    return set()


def apply_donor_fixes(donor):
    updated_fields = set()
    updated_fields |= make_donor_fields_title_case(donor)
    updated_fields |= fix_adress(donor)

    if updated_fields:
        donor.save(update_fields=updated_fields)
        donor.tags.add("info-auto-fixed")


SIGN_SEP = "~"
DONOR_TOKEN_MAX_AGE = 60 * 60 * 24 * 3  # 3 days


def get_signer(salt="donor-login-token"):
    return TimestampSigner(sep=SIGN_SEP, salt=salt)


def get_email_change_signer():
    return get_signer("donor-emailchange-token")


def get_str_to_sign(donor) -> str:
    return f"{donor.uuid}|{donor.last_login.isoformat() if donor.last_login else ''}"


def get_donor_login_token(donor):
    signer = get_signer()
    value = signer.sign(get_str_to_sign(donor)).split(SIGN_SEP, 1)[1]
    return value


def get_email_change_str_to_sign(donor: Donor, new_email: str) -> str:
    return f"{donor.uuid}|{new_email}"


def get_email_change_token(donor: Donor, new_email: str):
    signer = get_email_change_signer()
    value = signer.sign(get_email_change_str_to_sign(donor, new_email)).split(
        SIGN_SEP, 1
    )[1]
    return value


def validate_donor_token(donor_id, token) -> tuple[Donor | None, bool]:
    try:
        donor = Donor.objects.get(id=donor_id)
        sign_this = get_str_to_sign(donor)
    except Donor.DoesNotExist:
        # Bad donor id, we go through the signature check anyway to mitigate timing attacks
        sign_this = "-"
        donor = None

    signer = get_signer()
    signed_value = f"{sign_this}{SIGN_SEP}{token}"
    try:
        signer.unsign(signed_value, max_age=DONOR_TOKEN_MAX_AGE)
    except SignatureExpired:
        return donor, False
    except BadSignature:
        return donor, False
    if donor is None:
        return None, False
    return donor, True


def validate_email_change_token(
    donor_id: int, token: str, email: str | None
) -> tuple[Donor | None, str | None]:
    if email is None:
        return None, None
    try:
        donor = Donor.objects.get(id=donor_id)
        sign_this = get_email_change_str_to_sign(donor, email)
    except Donor.DoesNotExist:
        sign_this = "-"
        donor = None
    signer = get_email_change_signer()
    signed_value = f"{sign_this}{SIGN_SEP}{token}"
    try:
        signer.unsign(signed_value, max_age=DONOR_TOKEN_MAX_AGE)
    except SignatureExpired:
        return donor, None
    except BadSignature:
        return donor, None
    if donor is None:
        return None, None
    return donor, email


def get_donor_from_request(request) -> Donor | None:
    if donor_id := request.session.get(DONOR_SESSION_KEY):
        try:
            return Donor.objects.get(id=donor_id)
        except Donor.DoesNotExist:
            pass

    if not request.user.is_authenticated:
        return None
    donors = Donor.objects.filter(user=request.user, email_confirmed__isnull=False)
    if not donors:
        return None
    if len(donors) == 1:
        return donors[0]
    return merge_donor_list(donors)


def merge_donor_with_same_confirmed_emails(donor):
    email = donor.email
    other_donors = Donor.objects.filter(
        email=email, email_confirmed__isnull=False
    ).exclude(id=donor.id)
    if other_donors:
        merge_donor_list([donor] + list(other_donors))


def get_upgrade_amounts(amount: Decimal, interval: int):
    one = Decimal("1")
    amount_per_month = amount / interval
    step = None
    percentages = (15, 25, 35)
    new_amounts = set()
    if amount_per_month < 10:
        round_to = 1
        step = Decimal("5")
    elif amount_per_month < 25:
        round_to = 5
        step = Decimal("5")
    elif amount_per_month < 100:
        round_to = 5
    else:
        round_to = 10

    base_amount = amount_per_month
    if amount_per_month < 25:
        amount = (amount_per_month / step).quantize(one, ROUND_UP) * step
        if amount > amount_per_month:
            new_amounts.add(amount * interval)
            base_amount = amount

    def make_amount(base, add_extra):
        new_amount = base + add_extra
        new_amount = new_amount * interval
        new_amount = (new_amount / round_to).quantize(one, ROUND_UP) * round_to
        return new_amount

    if step is not None:
        for i in range(1, 4):
            new_amounts.add(make_amount(base_amount, step * i))
    else:
        for percent in percentages:
            extra = amount_per_month * percent / 100
            new_amounts.add(make_amount(amount_per_month, extra))
    return sorted(new_amounts)[:3]


def get_next_min_amount(amount):
    one = Decimal("1")
    return (amount + one).quantize(one, ROUND_DOWN)


def format_amount_interval(amount: Decimal, interval: int):
    return (
        _("{amount} Euro every year").format(amount=intcomma(amount))
        if interval == 12
        else ngettext_lazy(
            "{amount} Euro every month",
            "{amount} Euro every {interval} months",
            interval,
        ).format(amount=intcomma(amount), interval=interval)
    )


def format_interval(interval: int):
    return (
        _("every year")
        if interval == 12
        else ngettext_lazy(
            "every month",
            "every {interval} months",
            interval,
        ).format(interval=interval)
    )


def format_amount_with_currency(num: Decimal) -> str:
    return "{} {}".format(format_amount(num), settings.DEFAULT_CURRENCY_LABEL)


def format_decimal_amount_with_currency(num: Decimal) -> str:
    return "{} {}".format(format_decimal_amount(num), settings.DEFAULT_CURRENCY_LABEL)


def format_amount(num: Decimal) -> str:
    return intcomma(num)


def format_decimal_amount(num: Decimal) -> str:
    return floatformat(num, "2g")


def make_presets(presets: list[int]) -> list[tuple[int, str]]:
    return [
        (
            amount,
            "{amount} {currency}".format(
                amount=intcomma(amount), currency=settings.FROIDE_CONFIG["currency"]
            ),
        )
        for amount in presets
    ]
