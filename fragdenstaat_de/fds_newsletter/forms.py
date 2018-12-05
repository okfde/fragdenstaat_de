from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from froide.helper.widgets import BootstrapCheckboxInput

from newsletter.models import Newsletter, Subscription


class NewsletterUserExtra():
    def on_init(self, form):
        form.fields['newsletter'] = forms.BooleanField(
            required=False,
            widget=BootstrapCheckboxInput,
            label=_("Check if you want to receive our newsletter.")
        )

    def on_clean(self, form):
        pass

    def on_save(self, form, user):
        # FIXME: remove soon
        user.newsletter = form.cleaned_data['newsletter']

        if not form.cleaned_data['newsletter']:
            return

        try:
            newsletter = Newsletter.objects.get(
                slug=settings.DEFAULT_NEWSLETTER
            )
        except Newsletter.DoesNotExist:
            return

        Subscription.objects.create(
            user=user,
            newsletter=newsletter,
            subscribed=False,
            subscribe_date=timezone.now()
        )
