from froide.celery import app as celery_app

from fragdenstaat_de.theme.notifications import send_notification


@celery_app.task(name='fragdenstaat_de.fds_donation.new_donation')
def send_donation_notification(donation_id):
    from .models import Donation

    try:
        donation = Donation.objects.get(
            id=donation_id,
        )
    except Donation.DoesNotExist:
        return
    send_notification('Neue Spende: {amount} EUR'.format(
        amount=donation.amount
    ))
