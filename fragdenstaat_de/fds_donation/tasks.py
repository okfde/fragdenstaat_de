from django.utils import timezone

from dateutil.relativedelta import relativedelta
from fragdenstaat_de.theme.notifications import send_notification

from froide.celery import app as celery_app

TIME_ZERO = dict(hour=0, minute=0, second=0, microsecond=0)


@celery_app.task(name="fragdenstaat_de.fds_donation.new_donation")
def send_donation_notification(donation_id):
    from .models import Donation

    try:
        donation = Donation.objects.get(
            id=donation_id,
        )
    except Donation.DoesNotExist:
        return
    send_notification("Neue Spende: {amount} EUR".format(amount=donation.amount))


@celery_app.task(name="fragdenstaat_de.fds_donation.remind_unreceived_banktransfers")
def remind_unreceived_banktransfers():
    """
    To be run on the 15th of each month
    """
    from .models import Donation
    from .services import send_donation_reminder_email

    today = timezone.localtime(timezone.now())

    last_month = today - relativedelta(months=1)
    first_of_this_month = today.replace(day=1, **TIME_ZERO)
    first_of_last_month = last_month.replace(day=1, **TIME_ZERO)

    donations = Donation.objects.filter(
        completed=True,
        received=False,
        method="banktransfer",
        timestamp__gte=first_of_last_month,
        timestamp__lt=first_of_this_month,
    ).select_related("donor", "payment")

    for donation in donations:
        donation_from_donor_exists = (
            Donation.objects.filter(
                completed=True,
                received=True,
                donor_id=donation.donor_id,
                timestamp__gte=first_of_last_month,
                timestamp__lt=first_of_this_month,
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
    Donation.objects.filter(received=False, timestamp__lt=unreceived_last).delete()

    # Remove donors without donations
    Donor.objects.filter(donations=None).delete()


@celery_app.task(name="fragdenstaat_de.fds_donation.send_jzwb")
def send_jzwb_mailing_task(donor_id, year):
    from .export import send_jzwb_mailing
    from .models import Donor

    try:
        donor = Donor.objects.get(
            id=donor_id,
        )
    except Donor.DoesNotExist:
        return

    send_jzwb_mailing(donor, year)
