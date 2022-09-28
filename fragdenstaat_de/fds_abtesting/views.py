from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .forms import ABTestEventForm


@require_POST
def ab_test(request):
    form = ABTestEventForm(data=request.POST)
    if form.is_valid():
        event = form.save(request)
        return redirect(event.ab_test.action)
