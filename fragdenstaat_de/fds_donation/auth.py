from .models import Donor, Recurrence
from .services import confirm_donor_email
from .utils import merge_donor_list

DONOR_SESSION_KEY = "donor_id"


def check_subscription_access(request, subscription):
    donor = get_donor_from_request(request)
    if donor is None:
        return False
    if donor.user and subscription.customer.user:
        return donor.user == subscription.customer.user
    return Recurrence.objects.filter(donor=donor, subscription=subscription).exists()


def get_donor_from_request(request) -> Donor | None:
    if donor_id := request.session.get(DONOR_SESSION_KEY):
        try:
            return Donor.objects.get(id=donor_id)
        except Donor.DoesNotExist:
            pass

    if not request.user.is_authenticated:
        return None
    donors = Donor.objects.filter(user=request.user)
    if not donors:
        return None
    if len(donors) == 1:
        return donors[0]
    return merge_donor_list(donors)


def login_donor(request, donor, update_login=True):
    if update_login:
        confirm_donor_email(donor, request=request)
        donor.update_last_login()
    request.session[DONOR_SESSION_KEY] = donor.id


def logout_donor(request):
    try:
        del request.session[DONOR_SESSION_KEY]
    except KeyError:
        pass
