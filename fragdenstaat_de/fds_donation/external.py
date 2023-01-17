import re
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Q

import pandas as pd

from froide_payment.models import Payment, PaymentStatus
from froide_payment.provider.banktransfer import find_transfer_code

from .models import Donation, Donor
from .services import create_donation_from_payment, detect_recurring_on_donor


def find_donation(transfer_ident, row):
    try:
        return Donation.objects.get(identifier=transfer_ident)
    except Donation.DoesNotExist:
        pass

    transfer_code = find_transfer_code(row["reference"])

    if transfer_code is None:
        return None

    payments = Payment.objects.filter(transaction_id=transfer_code)
    if not payments:
        return None
    try:
        donation = Donation.objects.get(payment=payments[0], identifier="")
    except Donation.DoesNotExist:
        return None

    donor = donation.donor
    if donor:
        if not donor.attributes or "iban" not in donor.attributes:
            donor.attributes = donor.attributes or {}
            donor.attributes["iban"] = row["iban"]
            donor.save()
    return donation


def get_or_create_bank_transfer_donor(row):
    if pd.notnull(row["iban"]):
        donors = Donor.objects.filter(attributes__iban=row["iban"])
        if len(donors) > 0:
            return donors[0]

    name = row["name"]
    names = name.strip().rsplit(" ", 1)
    first_name = " ".join(names[:-1])
    last_name = " ".join(names[-1:])
    attrs = {}
    ident = ""
    country = ""
    if pd.notnull(row["iban"]):
        attrs = {"iban": row["iban"]}
        country = row["iban"][:2]
        ident = row["iban"]
    return Donor.objects.create(
        active=True,
        salutation="",
        first_name=first_name,
        last_name=last_name,
        company_name="",
        address="",
        postcode="",
        city="",
        country=country,
        email="",
        identifier=ident,
        attributes=attrs,
        contact_allowed=False,
        become_user=False,
        receipt=False,
    )


def import_banktransfer(transfer_ident, row, project):
    is_new = False
    donation = find_donation(transfer_ident, row)
    if donation is None:
        donor = get_or_create_bank_transfer_donor(row)
        donation = Donation(
            donor=donor,
            completed=True,
        )
        is_new = True
    else:
        donor = donation.donor

    donation.project = project
    donation.identifier = transfer_ident
    donation.amount = Decimal(str(row["amount"]))
    donation.amount_received = Decimal(str(row["amount"]))
    donation.received_timestamp = row["date_received"]
    if is_new:
        if pd.notnull(row["date"]) and row["date"]:
            donation.timestamp = row["date"]
        else:
            donation.timestamp = row["date_received"]
    donation.method = "banktransfer"
    donation.completed = True
    donation.save()

    detect_recurring_on_donor(donor)

    if donation.payment:
        payment = donation.payment
        if payment.status != PaymentStatus.CONFIRMED:
            payment.captured_amount = donation.amount
            payment.received_amount = donation.amount
            payment.received_timestamp = donation.received_timestamp
            payment.change_status(PaymentStatus.CONFIRMED)
            payment.save()
    return is_new


BLOCK_LIST = set(["Stripe Payments UK Ltd", "Stripe Technology Europe Ltd", "Stripe"])
DEBIT_PATTERN = re.compile(r" \(P(\d+)\)")


def update_direct_debit(row):
    match = DEBIT_PATTERN.search(row["reference"])
    try:
        payment = Payment.objects.get(id=int(match.group(1)))
    except Payment.DoesNotExist:
        return
    amount = Decimal(str(row["amount"]))
    payment.captured_amount = amount
    payment.received_amount = amount
    payment.received_timestamp = row["date_received"]
    payment.change_status(PaymentStatus.CONFIRMED)
    payment.save()


def import_banktransfers(xls_file, project):
    df = pd.read_excel(
        xls_file, engine="xlrd" if xls_file.name.endswith(".xls") else "openpyxl"
    )
    df = df.rename(
        columns={
            "Betrag": "amount",
            "Datum": "date_received",
            "Wertstellung": "date",
            "Name": "name",
            "Verwendungszweck": "reference",
            "Konto": "iban",
            "Bank": "bic",
        }
    )
    df = df.dropna(subset=["date_received"])
    df["date_received"] = df["date_received"].dt.tz_localize(settings.TIME_ZONE)
    if "date" in df.columns:
        df["date"] = df["date"].dt.tz_localize(settings.TIME_ZONE)
    else:
        df["date"] = None
    count = 0
    new_count = 0
    for i, row in df.iterrows():
        if row["name"] in BLOCK_LIST:
            continue
        if DEBIT_PATTERN.search(row["reference"]):
            update_direct_debit(row)
            continue
        local_date = row["date_received"].date()
        transfer_ident = "{date}-{ref}-{iban}-{i}".format(
            date=local_date.isoformat(), ref=row["reference"], iban=row["iban"], i=i
        )
        is_new = import_banktransfer(transfer_ident, row, project)
        count += 1
        if is_new:
            new_count += 1
    return count, new_count


def import_paypal(csv_file):
    df = pd.read_csv(csv_file)
    df["date"] = pd.to_datetime(
        df["Datum"] + " " + df["Uhrzeit"], format="%d.%m.%Y %H:%M:%S"
    ).dt.tz_localize(settings.TIME_ZONE)
    df["amount"] = pd.to_numeric(
        df["Brutto"].str.replace(".", "").str.replace(",", ".")
    )
    df["amount_received"] = pd.to_numeric(
        df["Netto"].str.replace(".", "").str.replace(",", ".")
    )

    df = df.rename(
        columns={
            "Transaktionscode": "sale_id",
            "Zugehöriger Transaktionscode": "subscription_id",
            "Name": "name",
            "Ländervorwahl": "country",
            "Adresszeile 1": "address",
            "Adresszusatz": "address2",
            "Ort": "city",
            "PLZ": "postcode",
            "Hinweis": "note",
            "Auswirkung auf Guthaben": "Guthaben",
            "Absender E-Mail-Adresse": "paypal_email",
        }
    )
    make_empty = (
        "country",
        "address",
        "address2",
        "city",
        "note",
        "postcode",
        "subscription_id",
    )

    df = df.query('Guthaben == "Haben"')
    for c in make_empty:
        df[c] = df[c].fillna("")

    df["address"] = df.apply(
        lambda r: "{} {}".format(r["address"], r["address2"]).strip(), 1
    )
    count = 0
    new_count = 0
    for _, row in df.iterrows():
        is_new = import_paypal_row(row)
        count += 1
        if is_new:
            new_count += 1
    return count, new_count


def get_or_create_paypal_donor(row):
    donor = (
        Donor.objects.filter(
            Q(attributes__paypal_email=row["paypal_email"])
            | Q(email=row["paypal_email"], email_confirmed__isnull=False)
        )
        .order_by("id")
        .first()
    )
    if donor is not None:
        return donor

    name = row["name"]
    names = name.strip().rsplit(" ", 1)
    first_name = " ".join(names[:-1])
    last_name = " ".join(names[-1:])
    return Donor.objects.create(
        active=True,
        salutation="",
        first_name=first_name,
        last_name=last_name,
        company_name="",
        address=row["address"],
        postcode=str(row["postcode"]),
        city=row["city"],
        country=row["country"],
        email=row["paypal_email"],
        attributes={"paypal_email": row["paypal_email"]},
        contact_allowed=False,
        become_user=False,
        receipt=False,
    )


def import_paypal_row(row):
    """
    - Find payment
    - If found return False
    - If not:
    - Create donation / donor
    """

    payment = find_paypal_payment(row)
    if payment:
        if not payment.received_amount:
            payment.received_amount = Decimal(str(row["amount_received"]))
        if not payment.received_timestamp:
            payment.received_timestamp = row["date"]
        payment.save()
        # Make sure has donation
        create_donation_from_payment(payment)
        return False

    try:
        return Donation.objects.get(method="paypal", identifier=row["sale_id"])
    except Donation.DoesNotExist:
        pass

    donor = get_or_create_paypal_donor(row)

    donation = Donation.objects.create(
        donor=donor,
        identifier=row["sale_id"],
        completed=True,
        received_timestamp=row["date"],
        timestamp=row["date"],
        method="paypal",
        amount=Decimal(str(row["amount"])),
        amount_received=Decimal(str(row["amount_received"])),
        note=row["note"],
        recurring=bool(row["subscription_id"]),
    )
    detect_recurring_on_donor(donor)

    return donation


def find_paypal_payment(row):
    buffer = timedelta(minutes=5)

    cond = Q(extra_data__contains=row["sale_id"])
    if row["subscription_id"]:
        cond |= Q(extra_data__contains=row["subscription_id"])

    payments = (
        Payment.objects.filter(
            variant="paypal",
            status=PaymentStatus.CONFIRMED,
        )
        .filter(created__gte=row["date"] - buffer, created__lte=row["date"] + buffer)
        .filter(cond)
    )

    if len(payments) == 0:
        return None
    elif len(payments) == 1:
        return payments[0]
    raise ValueError("Multiple matching payments found")
