from django.conf import settings
from django.db.models import Min

from fragdenstaat_de.fds_newsletter.utils import subscribe_to_newsletter

from .models import Donation, Donor, update_donation_numbers

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
    "identifier",
    "attributes",
    "email_confirmed",
    "contact_allowed",
    "receipt",
    "note",
    "invalid",
    "active",
    "user",
    "subscriber",
]


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
    merged_donor_data = {}
    for field in fields:
        best_value = None
        for donor in candidates:
            val = getattr(donor, field)
            if best_value is None:
                if isinstance(val, dict):
                    best_value = dict(val)
                else:
                    best_value = val
                continue
            if isinstance(val, dict):
                best_value.update(val)
            elif val:
                best_value = val
        if best_value is not None:
            merged_donor_data[field] = best_value

    merged_donor = Donor(**merged_donor_data)
    return merged_donor


def merge_donors(candidates, primary_id, validated_data=None):
    from .services import detect_recurring_on_donor

    # Collect old ids and references
    old_uuids = []
    old_ids = []
    subscriptions = []
    for candidate in candidates:
        if candidate.id == primary_id:
            continue
        old_uuids.append(str(candidate.uuid))
        old_ids.append(str(candidate.id))

        for sub in candidate.subscriptions.all():
            subscriptions.append(sub)

    merged_donor = [c for c in candidates if c.id == primary_id][0]

    if validated_data:
        # Set form data on primary
        for key, val in validated_data.items():
            setattr(merged_donor, key, val)

    # Add old ids to attributes
    attrs = merged_donor.attributes or {}

    old_val = attrs.get("old_uuids", "").split(",")
    old_uuids.extend([x for x in old_val if x])
    attrs["old_uuids"] = ",".join(old_uuids)

    old_val = attrs.get("old_ids", "").split(",")
    old_ids.extend([x for x in old_val if x])
    attrs["old_ids"] = ",".join(old_ids)

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
