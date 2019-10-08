from django import forms
from django.conf import settings
from django.utils import timezone

from froide.helper.widgets import BootstrapCheckboxInput

from newsletter.models import Newsletter, Subscription

from .utils import subscribe


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

        # User is not confirmed yet, so create subscription
        # tentatively, it will be subscribed=True
        # via account activation signal whena subscription is found
        Subscription.objects.update_or_create(
            user=user,
            newsletter=newsletter,
            defaults={
                'subscribed': False,
                'subscribe_date': timezone.now()
            }
        )


class DonorNewsletterExtra():
    def on_init(self, form):
        form.fields['donor_newsletter'] = forms.TypedChoiceField(
            widget=forms.RadioSelect,
            choices=(
                (1, 'Ja, ich möchte Neuigkeiten zur Verwendung meiner Spende erhalten!'),
                (0, 'Nein, ich möchte nicht erfahren, wie meine Spende verwendet wird.'),
            ),
            coerce=bool,
            required=True,
            label='Spendenverwendung',
            error_messages={
                'required': 'Sie müssen sich entscheiden.'
            },
        )

    def on_clean(self, form):
        pass

    def on_save(self, form, user):
        if not form.cleaned_data['donor_newsletter']:
            return

        try:
            newsletter = Newsletter.objects.get(
                slug=settings.DONOR_NEWSLETTER
            )
        except Newsletter.DoesNotExist:
            return
        subscribe(
            newsletter, form.cleaned_data['email'],
            user=user
        )
