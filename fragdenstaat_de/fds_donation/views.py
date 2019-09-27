from django.views.decorators.http import require_POST

from froide.helper.utils import get_redirect

from .forms import DonationGiftForm


@require_POST
def make_order(request, category):
    form = DonationGiftForm(data=request.POST, category=category)
    if form.is_valid():
        form.save(request)

    return get_redirect(request)
