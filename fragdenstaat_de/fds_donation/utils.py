import re

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import Min

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


def get_email(donors):
    return first(
        sorted(
            [d for d in donors if d.email and d.email_confirmed],
            key=lambda x: x.email_confirmed,
            reverse=True,
        ),
        default="",
        attr="email",
    )


def get_user(donors):
    proposed_email = get_email(donors)
    return first(
        [d.user for d in donors if d.user and d.user.email == proposed_email],
        default=None,
    )


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
        "email": get_email,
        "email_confirmed": get_latest("email_confirmed"),
        "contact_allowed": get_latest_known("contact_allowed"),
        "receipt": get_latest_known("contact_allowed"),
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
        old_data.append({f: str(getattr(candidate, f))} for f in old_fields)
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
            merged_donor.note += "\n\n---\n{old_address}\n---\n\n"
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


def get_signer():
    return TimestampSigner(sep=SIGN_SEP, salt="donor-login-token")


def get_str_to_sign(donor) -> str:
    return f"{donor.uuid}|{donor.last_login.isoformat() if donor.last_login else ''}"


def get_donor_login_token(donor):
    signer = get_signer()
    value = signer.sign(get_str_to_sign(donor)).split(SIGN_SEP, 1)[1]
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
