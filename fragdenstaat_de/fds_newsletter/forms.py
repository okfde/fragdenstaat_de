from django import forms
from django.conf import settings
from django.utils import timezone

from froide.helper.widgets import BootstrapCheckboxInput

from newsletter.models import Newsletter, Subscription


class NewsletterUserExtra():
    def on_init(self, form):
        form.fields['newsletter'] = forms.BooleanField(
            required=False,
            widget=BootstrapCheckboxInput,
            label="Erhalten Sie unseren Newsletter zum Thema Informationsfreiheit."
        )

    def on_clean(self, form):
        pass

    def on_save(self, form, user):
        user.newsletter = form.cleaned_data['newsletter']

        if not form.cleaned_data['newsletter']:
            return

        try:
            newsletter = Newsletter.objects.get(
                slug=settings.DEFAULT_NEWSLETTER
            )
        except Newsletter.DoesNotExist:
            return

        Subscription.objects.update_or_create(
            user=user,
            newsletter=newsletter,
            defaults={
                'subscribed': False,
                'subscribe_date': timezone.now()
            }
        )
