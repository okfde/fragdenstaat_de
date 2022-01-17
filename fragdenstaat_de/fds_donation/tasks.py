from django.utils import timezone

from dateutil.relativedelta import relativedelta

from froide.celery import app as celery_app

from fragdenstaat_de.theme.notifications import send_notification


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
    zero = dict(hour=0, minute=0, second=0, microsecond=0)

    last_month = today - relativedelta(months=1)
    first_of_this_month = today.replace(day=1, **zero)
    first_of_last_month = last_month.replace(day=1, **zero)

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
