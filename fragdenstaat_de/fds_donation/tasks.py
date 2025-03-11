import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import mail_managers
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dateutil.relativedelta import relativedelta

from froide.celery import app as celery_app

from fragdenstaat_de.theme.notifications import send_notification

TIME_ZERO = {"hour": 0, "minute": 0, "second": 0, "microsecond": 0}


@celery_app.task(name="fragdenstaat_de.fds_donation.new_donation")
def send_donation_notification(donation_id):
    from .models import Donation

    try:
        donation = Donation.objects.get(
            id=donation_id,
        )
    except Donation.DoesNotExist:
        return
    if donation.payment.is_deferred():
        send_notification(
            "🚨Zurückgehaltene Spende: {amount} EUR".format(amount=donation.amount)
        )
    else:
        send_notification("Neue Spende: {amount} EUR".format(amount=donation.amount))


@celery_app.task(name="fragdenstaat_de.fds_donation.remind_unreceived_banktransfers")
def remind_unreceived_banktransfers():
    """
    To be run on the 15th of each month
    Check if there are promised bank transfers in the last
    month that have not been received. Account for bank delays.
    """
    from .models import Donation
    from .services import send_donation_reminder_email

    today = timezone.localtime(timezone.now())

    bank_delay = relativedelta(days=4)
    last_month = today - relativedelta(months=1)
    first_of_this_month = today.replace(day=1, **TIME_ZERO)
    end_date = first_of_this_month - bank_delay
    first_of_last_month = last_month.replace(day=1, **TIME_ZERO)
    start_date = first_of_last_month - bank_delay

    donations = Donation.objects.filter(
        completed=True,
        received_timestamp__isnull=True,
        method="banktransfer",
        timestamp__gte=start_date,
        timestamp__lt=end_date,
    ).select_related("donor", "payment")

    for donation in donations:
        # Have we received any donations from this donor since?
        donation_from_donor_exists = (
            Donation.objects.filter(
                completed=True,
                received_timestamp__isnull=False,
                donor_id=donation.donor_id,
                timestamp__gte=start_date,
            )
            .exclude(id=donation.id)
            .exists()
        )
        if not donation_from_donor_exists:
            send_donation_reminder_email(donation)


@celery_app.task(name="fragdenstaat_de.fds_donation.remove_old_donations")
def remove_old_donations():
    from .models import Donation, Donor

    today = timezone.localtime(timezone.now())
    today = today.replace(**TIME_ZERO)

    # Remove donations that are incomplete and older than three months
    INCOMPLETE_AGE = relativedelta(months=3)
    incomplete_last = today - INCOMPLETE_AGE
    Donation.objects.filter(completed=False, timestamp__lt=incomplete_last).delete()

    # Remove donations that are unreceived and older than 12 months
    UNRECEIVED_AGE = relativedelta(months=12)
    unreceived_last = today - UNRECEIVED_AGE
    Donation.objects.filter(
        received_timestamp__isnull=True, timestamp__lt=unreceived_last
    ).delete()

    # Remove donors without donations
    Donor.objects.filter(donations=None).delete()


@celery_app.task(name="fragdenstaat_de.fds_donation.send_jzwb")
def send_jzwb_mailing_task(donor_id, year, set_receipt_date=True, store_backup=True):
    from .export import send_jzwb_mailing
    from .models import Donor

    try:
        donor = Donor.objects.get(
            id=donor_id,
        )
    except Donor.DoesNotExist:
        return

    send_jzwb_mailing(
        donor, year, set_receipt_date=set_receipt_date, store_backup=store_backup
    )


@celery_app.task(name="fragdenstaat_de.fds_donation.backup_jzwb_pdf")
def backup_jzwb_pdf_task(donor_id, year, ignore_receipt_date=None):
    from .export import backup_jzwb
    from .models import Donor

    try:
        donor = Donor.objects.get(
            id=donor_id,
        )
    except Donor.DoesNotExist:
        return

    backup_jzwb(donor, year, ignore_receipt_date=ignore_receipt_date)


@celery_app.task(name="fragdenstaat_de.fds_donation.import_banktransfers")
def import_banktransfers_task(filepath, project, user_id=None):
    from .external import import_banktransfers

    try:
        count, new_count = import_banktransfers(filepath, project)
    finally:
        os.remove(filepath)

    if user_id is not None:
        user = get_user_model().objects.get(id=user_id)
        user.send_mail(
            _("Bank transfers imported for {project}").format(project=project),
            _("Count: {count}\nNew: {new}").format(count=count, new=new_count),
        )


@celery_app.task(name="fragdenstaat_de.fds_donation.import_paypal")
def import_paypal_task(filepath, user_id=None):
    from .external import import_paypal

    try:
        count, new_count = import_paypal(filepath)
    finally:
        os.remove(filepath)

    if user_id is not None:
        user = get_user_model().objects.get(id=user_id)
        user.send_mail(
            _("Paypal imported"),
            _("Count: {count}\nNew: {new}").format(count=count, new=new_count),
        )


@celery_app.task(name="fragdenstaat_de.fds_donation.send_donation_tasks_update_mail")
def send_donation_tasks_update_mail():
    from froide_payment.models import PaymentStatus

    from .models import Donation, DonationGiftOrder

    messages = []

    WEEK = timedelta(days=7) + timedelta(hours=1)
    new_orders = DonationGiftOrder.objects.filter(
        timestamp__gte=timezone.now() - WEEK, shipped__isnull=True
    ).count()
    if new_orders > 0:
        order_admin = settings.SITE_URL + reverse(
            "admin:fds_donation_donationgiftorder_changelist"
        )
        messages.append(
            _("{count} new donation gift orders in the last week\n{url}").format(
                count=new_orders, url=order_admin
            )
        )

    deferred_donations = Donation.objects.filter(
        payment__status=PaymentStatus.DEFERRED,
    ).count()
    if deferred_donations > 0:
        deferred_admin = settings.SITE_URL + reverse(
            "admin:fds_donation_deferreddonation_changelist"
        )
        messages.append(
            _("{count} deferred donations\n{url}").format(
                count=deferred_donations, url=deferred_admin
            )
        )

    if messages:
        mail_managers(_("Donation Admin Tasks"), "\n\n".join(messages))
