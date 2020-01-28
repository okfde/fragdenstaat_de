from django.utils import timezone

from num2words import num2words


MAX_DONATIONS = 18


def format_number(num):
    return (u'%.2f €' % num).replace('.', ',')


def get_zwbs(donors, year=None):
    if year is None:
        # Default to last year
        year = timezone.now().year - 1

    for donor in donors:
        data = get_zwb(donor, year)
        if data:
            yield data


def get_zwb(donor, year):
    donations = donor.donations.all().filter(
        received=True,
        receipt_given=False,
        received_timestamp__year=year
    ).order_by('received_timestamp')

    if len(donations) > MAX_DONATIONS:
        raise ValueError('Too many donations for %s' % donor.id)
    if not donations:
        return

    total_amount = sum(donation.amount for donation in donations)

    if donor.company_name:
        address_name = donor.company_name
        if donor.last_name:
            address_name += '\nz.Hd. %s' % (
                ' '.join([donor.first_name, donor.last_name]).strip()
            )
    else:
        address_name = donor.get_full_name()

    donor_name = donor.get_full_name()

    data = {
        'Adressname': address_name,
        'Spendenname': donor_name,
        'Vorname': donor.first_name,
        'Nachname': donor.last_name,
        'Straße': donor.address,
        'PLZ': donor.postcode,
        'Ort': donor.city,
        'Land': donor.country.name,
        'Anrede': donor.get_salutation_display(),
        'Briefanrede': donor.get_salutation(),
        'Jahressumme': format_number(total_amount),
        'Jahressumme in Worten': '- %s Euro -' % (
            num2words(total_amount, lang='de')
        )
    }

    for i in range(1, MAX_DONATIONS + 1):
        if i > len(donations):
            data.update({
                'Datum%s' % i: '',
                'Betrag%s' % i: '',
            })
            continue
        donation = donations[i - 1]
        data.update({
            'Datum%s' % i: donation.received_timestamp.strftime('%d.%m.%Y'),
            'Betrag%s' % i: format_number(donation.amount),
        })

    return data
