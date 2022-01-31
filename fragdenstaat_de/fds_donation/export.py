import base64
from io import BytesIO

from datetime import datetime
from num2words import num2words

from django.utils import formats, timezone
from django.conf import settings

from filer.models.foldermodels import Folder

from froide.foirequest.pdf_generator import PDFGenerator
from froide.helper.email_sending import mail_registry


MAX_DONATIONS = 26


jzwb_mail = mail_registry.register(
    "fds_donation/email/jzwb", ("name", "salutation", "donor", "year", "total_amount")
)


def format_number(num):
    return ("%.2f €" % num).replace(".", ",")


def format_number_no_currency(num):
    return ("%.2f" % num).replace(".", ",")


def get_zwbs(donors, year):
    for donor in donors:
        data = get_zwb(donor, year)
        if data:
            yield data


def get_zwb(donor, year):
    donations = get_donations(donor, year)
    if not donations:
        return

    if len(donations) > MAX_DONATIONS:
        raise ValueError("Too many donations for %s" % donor.id)

    donation_data = get_donation_data(donations)

    return get_zwb_data(donor, donation_data)


def get_zwb_data(donor, donation_data):
    total_amount = sum(donation["amount"] for donation in donation_data)

    if donor.company_name:
        address_name = donor.company_name
        if donor.last_name:
            address_name += "\nz.Hd. %s" % (
                " ".join([donor.first_name, donor.last_name]).strip()
            )
    else:
        address_name = donor.get_full_name()

    donor_name = donor.get_company_name_or_name()

    donor_account = "Ihre Spendenübersicht finden Sie auch eingeloggt auf fragdenstaat.de. Melden Sie sich einfach bei uns, falls Sie noch nicht registriert sind."
    if donor.user_id:
        donor_account = "Ihre Spendenübersicht können Sie in Ihrem Nutzerkonto unter „Ihre Spenden“ einsehen."

    data = {
        "Adressname": address_name,
        "Spendenname": donor_name,
        "Vorname": donor.first_name,
        "Nachname": donor.last_name,
        "Strasse": donor.address,
        "PLZ": donor.postcode,
        "Ort": donor.city,
        "Land": donor.country.name,
        "Anrede": donor.get_salutation_display(),
        "Briefanrede": donor.get_german_salutation(),
        "Jahressumme": format_number_no_currency(total_amount),
        "JahressummeInWorten": amount_to_words(total_amount),
        "NutzerKonto": donor_account,
        "receipt_already": any(d["receipt_date"] for d in donation_data),
        "current_date": format_date(timezone.now()),
    }

    for i in range(1, MAX_DONATIONS + 1):
        if i > len(donation_data):
            data.update(
                {
                    "Datum%s" % i: "",
                    "Betrag%s" % i: "",
                    "Zuwendung%s" % i: "",
                    "Verzicht%s" % i: "",
                }
            )
            continue
        donation = donation_data[i - 1]
        data.update(
            {
                "Datum%s" % i: donation["date"],
                "Betrag%s" % i: donation["formatted_amount"],
                "Zuwendung%s" % i: "Geldzuwendung",
                "Verzicht%s" % i: "Nein",
            }
        )

    return data


def format_date(date):
    return formats.date_format(timezone.localtime(date), "SHORT_DATE_FORMAT")


def get_donations(donor, year):
    return (
        donor.donations.all()
        .filter(received=True, received_timestamp__year=year)
        .order_by("received_timestamp")
    )


def get_donation_data(donations):
    donations.update(export_date=timezone.now())

    return [
        {
            "date": format_date(donation.received_timestamp),
            "formatted_amount": format_number(donation.amount),
            "receipt_date": donation.receipt_date,
            "amount": donation.amount,
        }
        for donation in donations
    ]


def amount_to_words(amount):
    euro, cents = [int(x) for x in str(amount).split(".")]
    euro_word = num2words(euro, lang="de")
    if cents:
        cent_words = num2words(cents, lang="de")
        return "- %s Euro und %s Cent -" % (euro_word, cent_words)
    return "- %s Euro -" % euro_word


class ZWBPDFGenerator(PDFGenerator):
    template_name = "fds_donation/pdf/zwb.html"

    def __init__(self, obj, year=None):
        self.obj = obj
        if year is None:
            year = datetime.now().year - 1
        self.year = year

    def get_signature_string(self):
        try:
            folder = Folder.objects.get(name="Signature")
            files = folder.files
            if files and files.first().mime_type == "image/png":
                with open(files.first().path, "rb") as image_file:
                    return base64.b64encode(image_file.read()).decode("utf-8")
        except Folder.DoesNotExist:
            return ""

    def get_context_data(self, obj):
        ctx = super().get_context_data(obj)

        donations = get_donations(obj, self.year)
        donation_data = get_donation_data(donations)

        data = get_zwb_data(obj, donation_data)
        data["donations"] = donation_data
        data["year"] = self.year
        data["signature_string"] = self.get_signature_string()
        ctx.update(data)
        return ctx


class PostcodeEncryptedZWBPDFGenerator(ZWBPDFGenerator):
    def get_pdf_bytes(self):
        assert self.obj.postcode

        pdf_bytes = super().get_pdf_bytes()

        from PyPDF2 import PdfFileReader, PdfFileWriter

        input_pdf = PdfFileReader(BytesIO(pdf_bytes))

        output_pdf = PdfFileWriter()
        output_pdf.appendPagesFromReader(input_pdf)
        output_pdf.encrypt(self.obj.postcode)

        out_bytes = BytesIO()
        output_pdf.write(out_bytes)
        out_bytes.seek(0)
        return out_bytes.read()


def send_jzwb_mailing(donor, year, priority=False):
    if not donor.email:
        return

    pdf_generator = PostcodeEncryptedZWBPDFGenerator(donor, year=year)

    attachment = (
        "jzwb-fds-%d.pdf" % year,
        pdf_generator.get_pdf_bytes(),
        "application/pdf",
    )

    donations = get_donations(donor, year)
    total_amount = sum(donation["amount"] for donation in donations)

    context = {
        "year": year,
        "donor": donor,
        "name": donor.get_full_name(),
        "salutation": donor.get_salutation(),
        "total_amount": format_number_no_currency(total_amount),
    }

    jzwb_mail.send(
        email=donor.email,
        context=context,
        ignore_active=True,
        priority=priority,
        bcc=[settings.DEFAULT_FROM_EMAIL],
        attachments=[attachment],
    )

    # Update receipt date
    donations.update(receipt_date=timezone.now())
