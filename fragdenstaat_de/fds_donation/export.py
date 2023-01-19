import base64
import zipfile
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Optional

from django import forms
from django.http import HttpResponse, StreamingHttpResponse
from django.utils import formats, timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from filer.models.foldermodels import Folder
from fragdenstaat_de.fds_donation.remote_filing import backup_donation_file
from fragdenstaat_de.fds_donation.tasks import (
    backup_jzwb_pdf_task,
    send_jzwb_mailing_task,
)
from num2words import num2words

from froide.foirequest.pdf_generator import PDFGenerator
from froide.helper.csv_utils import dict_to_csv_stream, export_csv_response
from froide.helper.email_sending import mail_registry

from .models import Donor

MAX_DONATIONS_PER_PAGE = 26


class JZWBExportForm(forms.Form):
    year = forms.IntegerField(min_value=2018, max_value=timezone.now().year)
    export_format = forms.ChoiceField(
        choices=(
            ("pdf_encrypted", _("PDF (encrypted)")),
            ("pdf", _("PDF")),
            ("csv", _("CSV")),
            ("send_mailing", _("Send mailing")),
        )
    )
    store_backup = forms.BooleanField(
        required=False,
        label=_("Store backup"),
        help_text=_("A backup of generated document will be stored."),
    )
    set_receipt_date = forms.BooleanField(
        required=False,
        label=_("Set receipt date"),
        help_text=_("The donations will be marked as receipted."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["year"].initial = timezone.now().year - 1

    def make_response(self, queryset):
        export_format = self.cleaned_data["export_format"]

        result = self.run_export(queryset)
        if result is None:
            return

        if export_format == "csv":
            return export_csv_response(result)

        queryset = self.get_donors(queryset)

        if queryset.count() == 1:
            donor = queryset[0]
            response = HttpResponse(result, content_type="application/pdf")
            filename = "%s_%s_%s.pdf" % (
                slugify(donor.get_order_name()),
                donor.id,
                self.cleaned_data["year"],
            )
            response["Content-Disposition"] = 'attachment; filename="%s"' % filename
            return response

        response = StreamingHttpResponse(result, content_type="application/zip")
        response["Content-Disposition"] = (
            'attachment; filename="jzwbs_%d.zip"' % self.cleaned_data["year"]
        )
        return response

    def run_export(self, queryset=None):
        year = self.cleaned_data["year"]
        export_format = self.cleaned_data["export_format"]
        store_backup = self.cleaned_data["store_backup"]
        set_receipt_date = self.cleaned_data["set_receipt_date"]

        queryset = self.get_donors(queryset)

        result = None
        if export_format == "csv":
            zwbs_data = get_zwbs(queryset, year=year)
            result = dict_to_csv_stream(zwbs_data)
        elif export_format == "pdf":
            result = self.get_pdf(queryset, year)
        elif export_format == "pdf_encrypted":
            result = self.get_pdf(
                queryset, year, pdf_class=PostcodeEncryptedZWBPDFGenerator
            )
        elif export_format == "send_mailing":
            self.send_mailing(
                queryset,
                year,
                set_receipt_date=set_receipt_date,
                store_backup=store_backup,
            )

        if export_format != "send_mailing":
            receipt_date = None
            if set_receipt_date:
                receipt_date = timezone.now()
            for donor in queryset:
                if set_receipt_date:
                    donations = get_donations(donor, year)
                    # Update receipt date after export
                    donations.filter(receipt_date__isnull=True).update(
                        receipt_date=receipt_date
                    )
                if store_backup:
                    backup_jzwb_pdf_task.delay(
                        donor.pk, year, ignore_receipt_date=receipt_date
                    )

        return result

    def get_donors(self, queryset):
        # Filter by ZWB criteria
        # Only valid records
        queryset = queryset.filter(invalid=False)

        # Received donations in given year that have not yet been ZWBed
        # year = self.cleaned_data["year"]
        # donations_filter = Q(
        #     donations__amount_received__gt=0,
        #     donations__receipt_date__isnull=True,
        #     donations__received_timestamp__year=year,
        # )

        # queryset = queryset.annotate(
        #     amount_total=Sum("donations__amount", filter=donations_filter)
        # )

        queryset = queryset.order_by("last_name", "first_name")
        return queryset

    def get_pdf(self, queryset, year: int, pdf_class=None):
        if pdf_class is None:
            pdf_class = ZWBPDFGenerator

        if queryset.count() == 1:
            donor = queryset[0]
            pdf_generator = pdf_class(donor, year=year)
            return pdf_generator.get_pdf_bytes()

        return generate_pdf_zip_package(
            queryset.iterator(), year=year, pdf_class=pdf_class
        )

    def send_mailing(
        self,
        queryset,
        year: int,
        set_receipt_date: bool = True,
        store_backup: bool = True,
    ):

        queryset = (
            queryset.exclude(postcode="")
            .exclude(email="")
            .exclude(email_confirmed__isnull=True)
        )

        for donor in queryset:
            send_jzwb_mailing_task.delay(
                donor.id,
                year,
                set_receipt_date=set_receipt_date,
                store_backup=store_backup,
            )


jzwb_mail = mail_registry.register(
    "fds_donation/email/jzwb", ("name", "salutation", "donor", "year", "total_amount")
)


def format_number(num: Decimal) -> str:
    return ("%.2f €" % num).replace(".", ",")


def format_number_no_currency(num: Decimal) -> str:
    return ("%.2f" % num).replace(".", ",")


def get_zwbs(donors, year: int):
    for donor in donors:
        data = get_zwb(donor, year)
        if data:
            yield data


def get_zwb(donor: Donor, year: int):
    donations = get_donations(donor, year)
    if not donations:
        return

    if len(donations) > MAX_DONATIONS_PER_PAGE:
        raise ValueError("Too many donations for %s" % donor.id)

    donation_data = get_donation_data(donations)

    return get_zwb_data(donor, donation_data)


def get_zwb_data(donor: Donor, donation_data):
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

    for i in range(1, MAX_DONATIONS_PER_PAGE + 1):
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


def get_donations(donor: Donor, year: int):
    return (
        donor.donations.all()
        .filter(received_timestamp__year=year)
        .order_by("received_timestamp")
    )


def get_donation_data(donations, ignore_receipt_date: Optional[datetime] = None):
    donations.update(export_date=timezone.now())

    return [
        {
            "date": format_date(donation.received_timestamp),
            "formatted_amount": format_number(donation.amount),
            "receipt_date": donation.receipt_date > ignore_receipt_date
            if ignore_receipt_date is not None
            else bool(donation.receipt_date),
            "amount": donation.amount,
        }
        for donation in donations
    ]


def amount_to_words(amount: Decimal) -> str:
    euro, cents = [int(x) for x in str(amount).split(".")]
    euro_word = num2words(euro, lang="de")
    if cents:
        cent_words = num2words(cents, lang="de")
        return "- %s Euro und %s Cent -" % (euro_word, cent_words)
    return "- %s Euro -" % euro_word


class ZWBPDFGenerator(PDFGenerator):
    template_name = "fds_donation/pdf/zwb.html"

    def __init__(self, obj, year, ignore_receipt_date=None):
        self.obj = obj
        self.year = year
        self.ignore_receipt_date = ignore_receipt_date

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
        donation_data = get_donation_data(
            donations, ignore_receipt_date=self.ignore_receipt_date
        )

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


def send_jzwb_mailing(
    donor: Donor,
    year: int,
    priority: bool = False,
    store_backup: bool = True,
    set_receipt_date: bool = True,
):
    if not donor.email:
        return
    if not donor.email_confirmed:
        return
    if not donor.postcode:
        return

    pdf_generator = PostcodeEncryptedZWBPDFGenerator(donor, year=year)

    pdf_bytes = pdf_generator.get_pdf_bytes()

    attachment = (
        "jzwb-fds-%d.pdf" % year,
        pdf_bytes,
        "application/pdf",
    )

    donations = get_donations(donor, year)
    total_amount = sum(donation.amount for donation in donations)

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
        attachments=[attachment],
    )

    receipt_date = None
    if set_receipt_date:
        receipt_date = timezone.now()
        # Update receipt date after export
        donations.filter(receipt_date__isnull=True).update(receipt_date=receipt_date)
    if store_backup:
        backup_jzwb(donor, year, pdf_bytes=pdf_bytes, ignore_receipt_date=receipt_date)


def backup_jzwb(
    donor: Donor,
    year: int,
    pdf_bytes: Optional[bytes] = None,
    ignore_receipt_date: Optional[datetime] = None,
):
    pdf_generator = PostcodeEncryptedZWBPDFGenerator(
        donor, year=year, ignore_receipt_date=ignore_receipt_date
    )
    if pdf_bytes is None:
        pdf_bytes = pdf_generator.get_pdf_bytes()
    pdf_file = BytesIO(pdf_bytes)
    pdf_file_name = "jzwb-%s-%d.pdf" % (donor.pk, year)
    backup_donation_file(pdf_file, pdf_file_name)


class FakeFile:
    def __init__(self):
        self.inner_file = None

    def flush(self):
        pass

    def write(self, chunk):
        if self.inner_file is None:
            self.inner_file = BytesIO()
        self.inner_file.write(chunk)
        return len(chunk)

    def get_chunk(self):
        if self.inner_file is None:
            return None
        val = self.inner_file.getvalue()
        self.inner_file = None
        return val


def generate_pdf_zip_package(
    donors, year: int, pdf_class=PostcodeEncryptedZWBPDFGenerator
):
    fake_file = FakeFile()
    with zipfile.ZipFile(fake_file, "w") as zip_file:
        for donor in donors:
            pdf_generator = pdf_class(donor, year=year)
            attachment_name = "jzwb-fds-%d-%d.pdf" % (year, donor.id)
            zip_file.writestr(attachment_name, pdf_generator.get_pdf_bytes())
            chunk = fake_file.get_chunk()
            if chunk:
                yield chunk

    chunk = fake_file.get_chunk()
    if chunk:
        yield chunk


def get_pdf_zip_package(
    fp, donors, year: int, pdf_class=PostcodeEncryptedZWBPDFGenerator
):
    for chunk in generate_pdf_zip_package(donors, year, pdf_class=pdf_class):
        fp.write(chunk)
