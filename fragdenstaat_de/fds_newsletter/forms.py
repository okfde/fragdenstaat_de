from io import StringIO

from django import forms
from django.conf import settings
from django.forms import ModelForm, ValidationError
from django.utils.translation import gettext_lazy as _

from froide.helper.spam import SpamProtectionMixin
from froide.helper.widgets import BootstrapCheckboxSelectMultiple, BootstrapRadioSelect

from fragdenstaat_de.fds_mailing.models import EmailTemplate

from .models import Newsletter, Subscriber, UnsubscribeFeedback
from .utils import import_csv, subscribe, subscribed_newsletters


class NewsletterForm(SpamProtectionMixin, forms.Form):
    SPAM_PROTECTION = {
        "captcha": "ip",
        "action": "newsletter",
        "action_limit": 3,
        "action_block": True,
    }

    email = forms.EmailField(
        label=_("Email"),
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
            }
        ),
    )
    reference = forms.CharField(required=False, widget=forms.HiddenInput())
    keyword = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.request.user.is_authenticated:
            self.fields["email"].initial = self.request.user.email

    def clean_reference(self):
        # Avoid validation error, just cut off
        return self.cleaned_data["reference"][:255]

    def clean_keyword(self):
        # Avoid validation error, just cut off
        return self.cleaned_data["keyword"][:255]

    def save(self, newsletter, user):
        email = self.cleaned_data["email"]
        reference = self.cleaned_data["reference"]
        keyword = self.cleaned_data["keyword"]

        return subscribe(
            newsletter, email, user=user, reference=reference, keyword=keyword
        )


FORM_REFERENCE = "settings"


class NewslettersUserForm(forms.Form):
    newsletters = forms.ModelMultipleChoiceField(
        label=_("Newsletters"),
        queryset=Newsletter.objects.get_visible().filter(visible=True),
        required=False,
        widget=BootstrapCheckboxSelectMultiple,
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        subscribed_nls = list(subscribed_newsletters(self.user))
        self.fields["newsletters"].initial = subscribed_nls

    def save(self):
        chosen_newsletters = set(self.cleaned_data["newsletters"])
        newsletters = Newsletter.objects.get_visible()
        for newsletter in newsletters:
            wants_nl = newsletter in chosen_newsletters
            try:
                subscriber = Subscriber.objects.get(
                    user=self.user, newsletter=newsletter
                )
                if wants_nl:
                    if not subscriber.subscribed:
                        subscriber.reference = FORM_REFERENCE
                        subscriber.subscribe()
                else:
                    subscriber.unsubscribe(method=FORM_REFERENCE)
            except Subscriber.DoesNotExist:
                if wants_nl:
                    subscriber = Subscriber.objects.create(
                        newsletter=newsletter, user=self.user, reference=FORM_REFERENCE
                    )
                    subscriber.subscribe()


class NewsletterUserExtra:
    def on_init(self, form):
        form.fields["newsletter"] = forms.TypedChoiceField(
            widget=forms.RadioSelect,
            choices=(
                (
                    1,
                    "Ja, ich möchte den Newsletter zum Thema Informationsfreiheit erhalten!",
                ),
                (0, "Nein, ich möchte keinen Newsletter."),
            ),
            coerce=lambda x: bool(int(x)),
            required=True,
            label="Newsletter",
            error_messages={"required": "Sie müssen sich entscheiden."},
        )

    def on_clean(self, form):
        pass

    def on_save(self, form, user):
        if not form.cleaned_data.get("newsletter"):
            return

        try:
            newsletter = Newsletter.objects.get(slug=settings.DEFAULT_NEWSLETTER)
        except Newsletter.DoesNotExist:
            return

        # User is not confirmed yet, so create subscription
        # tentatively, it will be subscribed
        # via account activation signal when a user subscription is found
        Subscriber.objects.get_or_create(
            user=user, newsletter=newsletter, defaults={"reference": "user_extra"}
        )


class NewsletterFollowExtra(NewsletterUserExtra):
    def on_save(self, form, user):
        """
        successful follow and newsletter in follow context
        will create confirmed subscription
        """
        pass


class SubscriberImportForm(forms.Form):
    csv_file = forms.FileField(
        label=_("CSV file"),
        help_text=_(
            "Requires an email column. Optionally, name (or first_name, last_name) can be provided."
        ),
    )
    reference = forms.CharField(label=_("Import reference label"), required=True)
    email_confirmed = forms.BooleanField(
        label=_("Email addresses are confirmed"), required=False
    )

    def clean_email_confirmed(self):
        email_confirmed = self.cleaned_data["email_confirmed"]

        if not email_confirmed:
            try:
                EmailTemplate.objects.get(
                    mail_intent="fds_newsletter/email/subscriber_batch_confirm",
                    active=True,
                )
            except (EmailTemplate.DoesNotExist, EmailTemplate.MultipleObjectsReturned):
                raise ValidationError(
                    _(
                        "Make sure there exists one active mailing template for the batch confirm intent (fds_newsletter/email/subscriber_batch_confirm)."
                    )
                ) from None

        return email_confirmed

    def save(self, newsletter):
        csv_file = self.cleaned_data["csv_file"]
        csv_file = StringIO(csv_file.read().decode("utf-8"))
        import_csv(
            csv_file,
            newsletter,
            reference=self.cleaned_data["reference"],
            email_confirmed=self.cleaned_data["email_confirmed"],
        )


class UnsubscribeFeedbackForm(ModelForm):
    class Meta:
        model = UnsubscribeFeedback
        fields = ["reason", "comment"]
        widgets = {
            "reason": BootstrapRadioSelect,
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": "3",
                    "placeholder": _("Anything else you want to tell us?"),
                }
            ),
        }
