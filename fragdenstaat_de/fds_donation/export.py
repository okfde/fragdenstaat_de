from datetime import datetime
from num2words import num2words

from froide.foirequest.pdf_generator import PDFGenerator


MAX_DONATIONS = 18


def format_number(num):
    return (u'%.2f €' % num).replace('.', ',')


def get_zwbs(donors, year):
    for donor in donors:
        data = get_zwb(donor, year)
        if data:
            yield data


def get_zwb(donor, year):
    donations = get_donations(donor, year)
    if not donations:
        return
    return get_zwb_data(donor, donations)


def get_zwb_data(donor, donations):
    total_amount = sum(donation['amount'] for donation in donations)

    if donor.company_name:
        address_name = donor.company_name
        if donor.last_name:
            address_name += '\nz.Hd. %s' % (
                ' '.join([donor.first_name, donor.last_name]).strip()
            )
    else:
        address_name = donor.get_full_name()

    donor_name = donor.get_full_name()

    donor_account = 'Ihre Spendenübersicht finden Sie auch eingeloggt auf fragdenstaat.de. Melden Sie sich einfach bei uns, falls Sie noch nicht registriert sind.'
    if donor.user_id:
        donor_account = 'Ihre Spendenübersicht können Sie in Ihrem Nutzerkonto unter „Ihre Spenden“ einsehen.'

    data = {
        'Adressname': address_name,
        'Spendenname': donor_name,
        'Vorname': donor.first_name,
        'Nachname': donor.last_name,
        'Strasse': donor.address,
        'PLZ': donor.postcode,
        'Ort': donor.city,
        'Land': donor.country.name,
        'Anrede': donor.get_salutation_display(),
        'Briefanrede': donor.get_salutation(),
        'Jahressumme': format_number(total_amount),
        'JahressummeInWorten': amount_to_words(total_amount),
        'NutzerKonto': donor_account
    }

    for i in range(1, MAX_DONATIONS + 1):
        if i > len(donations):
            data.update({
                'Datum%s' % i: '',
                'Betrag%s' % i: '',
                'Zuwendung%s' % i: '',
                'Verzicht%s' % i: '',
            })
            continue
        donation = donations[i - 1]
        data.update({
            'Datum%s' % i: donation['date'],
            'Betrag%s' % i: donation['formatted_amount'],
            'Zuwendung%s' % i: 'Geldzuwendung',
            'Verzicht%s' % i: 'Nein',
        })

    return data


def get_donations(donor, year):
    donations = donor.donations.all().filter(
        received=True,
        receipt_given=False,
        received_timestamp__year=year
    ).order_by('received_timestamp')

    if len(donations) > MAX_DONATIONS:
        raise ValueError('Too many donations for %s' % donor.id)
    if not donations:
        return
    return [{
        'date': donation.received_timestamp.strftime('%d.%m.%Y'),
        'formatted_amount': format_number(donation.amount),
        'amount': donation.amount
    } for donation in donations]


def amount_to_words(amount):
    euro, cents = [int(x) for x in str(amount).split('.')]
    euro_word = num2words(euro, lang='de')
    if cents:
        cent_words = num2words(cents, lang='de')
        return '- %s Euro und %s Cent -' % (
            euro_word, cent_words
        )
    return '- %s Euro -' % euro_word


class ZWBPDFGenerator(PDFGenerator):
    template_name = 'fds_donation/pdf/zwb.html'

    def get_context_data(self, obj):
        ctx = super().get_context_data(obj)
        year = datetime.now().year - 1
        donations = get_donations(obj, year)

        data = get_zwb_data(obj, donations)
        data['donations'] = donations
        data['year'] = year

        ctx.update(data)
        return ctx
