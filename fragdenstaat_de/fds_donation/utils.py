from django.conf import settings

from fragdenstaat_de.fds_newsletter.utils import subscribe_to_newsletter


def subscribe_donor_newsletter(donor, email_confirmed=False):
    subscribe_to_newsletter(
        settings.DONOR_NEWSLETTER, donor.email, user=donor.user,
        name=donor.get_full_name(),
        email_confirmed=email_confirmed
    )
