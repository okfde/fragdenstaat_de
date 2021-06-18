from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from froide.helper.spam import SpamProtectionMixin

from .utils import subscribe
from .models import Newsletter, Subscriber


class NewsletterForm(SpamProtectionMixin, forms.Form):
    SPAM_PROTECTION = {
        'captcha': 'ip',
        'action': 'newsletter',
        'action_limit': 3,
        'action_block': True
    }

    email = forms.EmailField(
        label=_("Email"),
        required=True,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
            }
        )
    )
    reference = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    keyword = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.request.user.is_authenticated:
            self.fields['email'].initial = self.request.user.email

    def save(self, newsletter, user):
        email = self.cleaned_data['email']
        reference = self.cleaned_data['reference']
        keyword = self.cleaned_data['keyword']

        return subscribe(
            newsletter, email, user=user,
            reference=reference, keyword=keyword
        )


FORM_REFERENCE = 'settings'


class NewslettersUserForm(forms.Form):
    newsletters = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        newsletters = Newsletter.objects.get_visible()
        subscribed_nls = list(Subscriber.objects.filter(
            newsletter__in=newsletters,
            user=self.user,
            subscribed__isnull=False
        ).values_list('newsletter_id', flat=True))
        self.fields['newsletters'].queryset = newsletters
        self.fields['newsletters'].initial = subscribed_nls

    def save(self):
        chosen_newsletters = set(self.cleaned_data['newsletters'])
        newsletters = Newsletter.objects.get_visible()
        for newsletter in newsletters:
            wants_nl = newsletter in chosen_newsletters
            try:
                subscriber = Subscriber.objects.get(
                    user=self.user,
                    newsletter=newsletter
                )
                if wants_nl:
                    if not subscriber.subscribed:
                        subscriber.reference = FORM_REFERENCE
                        subscriber.subscribe()
                else:
                    subscriber.unsubscribe()
                return
            except Subscriber.DoesNotExist:
                if wants_nl:
                    subscriber = Subscriber.objects.create(
                        newsletter=newsletter,
                        user=self.user,
                        reference=FORM_REFERENCE
                    )
                    subscriber.subscribe()


class NewsletterUserExtra():
    def on_init(self, form):
        form.fields['newsletter'] = forms.TypedChoiceField(
            widget=forms.RadioSelect,
            choices=(
                (1, 'Ja, ich möchte den Newsletter zum Thema Informationsfreiheit erhalten!'),
                (0, 'Nein, ich möchte keinen Newsletter.'),
            ),
            coerce=lambda x: bool(int(x)),
            required=True,
            label='Newsletter',
            error_messages={
                'required': 'Sie müssen sich entscheiden.'
            },
        )

    def on_clean(self, form):
        pass

    def on_save(self, form, user):
        if not form.cleaned_data.get('newsletter'):
            return

        try:
            newsletter = Newsletter.objects.get(
                slug=settings.DEFAULT_NEWSLETTER
            )
        except Newsletter.DoesNotExist:
            return

        # User is not confirmed yet, so create subscription
        # tentatively, it will be subscribed
        # via account activation signal when a user subscription is found
        Subscriber.objects.get_or_create(
            user=user,
            newsletter=newsletter,
            defaults={
                'reference': 'user_extra'
            }
        )


class NewsletterFollowExtra(NewsletterUserExtra):
    def on_save(self, form, user):
        """
        successful follow and newsletter in follow context
        will create confirmed subscription
        """
        pass
