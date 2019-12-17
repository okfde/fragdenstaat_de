from decimal import Decimal

import pandas as pd

from froide_payment.models import Payment, PaymentStatus
from froide_payment.provider.banktransfer import TRANSFER_RE

from .models import Donor, Donation


def find_donation(transfer_ident, row):
    try:
        return Donation.objects.get(
            identifier=transfer_ident
        )
    except Donation.DoesNotExist:
        pass

    match = TRANSFER_RE.search(row['reference'])
    if match is None:
        return None

    payments = Payment.objects.filter(
        transaction_id=match.group(0).upper()
    )
    if not payments:
        return None
    try:
        donation = Donation.objects.get(
            payment=payments[0],
            identifier=''
        )
    except Donation.DoesNotExist:
        return None

    donor = donation.donor
    if donor and not donor.identifier:
        donor.identifier = row['iban']
        donor.save()
    return donation


def get_or_create_donor(row):
    try:
        return Donor.objects.get(
            identifier=row['iban']
        )
    except Donor.DoesNotExist:
        pass
    name = row['name']
    names = name.strip().rsplit(' ', 1)
    first_name = ' '.join(names[:-1])
    last_name = ' '.join(names[-1:])
    return Donor.objects.create(
        active=True,
        salutation='',
        first_name=first_name,
        last_name=last_name,
        company_name='',
        address='',
        postcode='',
        city='',
        country=row['iban'][:2],
        email='',
        identifier=row['iban'],
        contact_allowed=False,
        become_user=False,
        receipt=False,
    )


def import_banktransfer(transfer_ident, row):
    is_new = False
    donation = find_donation(transfer_ident, row)
    if donation is None:
        donor = get_or_create_donor(row)
        donation = Donation(
            donor=donor,
            completed=True,
            received=True,
        )
        is_new = True

    donation.identifier = transfer_ident
    donation.amount = Decimal(str(row['amount']))
    donation.received_timestamp = row['date_received']
    if is_new:
        donation.timestamp = row['date']
    donation.method = 'banktransfer'
    donation.received = True
    donation.completed = True
    donation.save()

    if donation.payment:
        payment = donation.payment
        if payment.status != PaymentStatus.CONFIRMED:
            payment.captured_amount = donation.amount
            payment.received_amount = donation.amount
            payment.change_status(PaymentStatus.CONFIRMED)
    return is_new


def import_banktransfers(xls_file):
    df = pd.read_excel(xls_file)
    df = df.rename(columns={
        'Betrag': 'amount',
        'Datum': 'date',
        'Wertstellung': 'date_received',
        'Name': 'name',
        'Verwendungszweck': 'reference',
        'Konto': 'iban',
        'Bank': 'bic'
    })

    count = 0
    new_count = 0
    for i, row in df.iterrows():
        transfer_ident = '{date}-{ref}-{iban}-{i}'.format(
            date=row['date'],
            ref=row['reference'],
            iban=row['iban'],
            i=i
        )
        is_new = import_banktransfer(transfer_ident, row)
        count += 1
        if is_new:
            new_count += 1
    return count, new_count
