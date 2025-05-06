from django import forms
from django.contrib.admin import widgets
from django.utils.translation import gettext_lazy as _

from fragdenstaat_de.fds_newsletter.models import Newsletter, Segment
from fragdenstaat_de.fds_newsletter.utils import generate_random_split

from . import MailingPreviewContextProvider, gather_mailing_preview_context
from .models import Mailing


class PreviewMailingForm(forms.Form):
    via_form = forms.BooleanField(
        label=_("Send via form"),
        initial=True,
        required=False,
        widget=forms.HiddenInput,
    )

    def __init__(self, *args, **kwargs):
        self.emailtemplate = kwargs.pop("emailtemplate", None)
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.providers: list[MailingPreviewContextProvider] = [
            provider
            for _receiver, provider in gather_mailing_preview_context.send(
                sender=self.emailtemplate
            )
        ]
        for provider in self.providers:
            if provider.options:
                self.fields[provider.name] = forms.ChoiceField(
                    label=provider.name.replace("_", " ").capitalize(),
                    required=False,
                    initial=self.request.GET.get(provider.name, ""),
                    choices=list(provider.options.items()),
                )

    @classmethod
    def from_request(cls, emailtemplate, request):
        if request.method != "GET":
            return cls(emailtemplate=emailtemplate, request=request)
        if "via_form" in request.GET:
            form = cls(emailtemplate=emailtemplate, request=request, data=request.GET)
            form.store(request)
            return form
        return cls(
            emailtemplate=emailtemplate,
            request=request,
            data=request.session.get("preview_mailing", None),
        )

    def store(self, request):
        if self.is_valid():
            data = self.cleaned_data.copy()
            if "via_form" in data:
                data.pop("via_form")
                request.session["preview_mailing"] = data

    def get_context(self):
        context = {}
        for provider in self.providers:
            value = self.cleaned_data.get(provider.name)
            if value or not provider.options:
                ctx = provider.provide_context(value, self.request)
                if ctx:
                    context.update(ctx)
        return context


class RandomSplitForm(forms.Form):
    name = forms.CharField(
        label=_("Name"),
        required=True,
        help_text=_("Unique name name for this split test"),
    )
    newsletter = forms.ModelChoiceField(Newsletter.objects.all(), required=True)
    segments = forms.ModelMultipleChoiceField(Segment.objects.all(), required=False)
    groups = forms.CharField(
        label=_("Groups"),
        required=True,
        help_text=_("e.g. 20,20"),
        initial="20,20",
    )

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

        self.fields["segments"].widget = widgets.FilteredSelectMultiple(
            "Segments", False, choices=[(x.id, str(x)) for x in Segment.objects.all()]
        )

    def clean_groups(self):
        groups = self.cleaned_data["groups"].split(",")
        try:
            groups = [int(g.strip()) for g in groups]
        except ValueError as e:
            raise forms.ValidationError(
                _("Please enter a comma separated list of integers.")
            ) from e
        group_total = sum(groups)
        if group_total > 100:
            raise forms.ValidationError(
                _(
                    "The sum of the groups must not be greater than 100. You entered {}."
                ).format(group_total)
            )
        return groups

    def save(self, user):
        target_segments = generate_random_split(
            self.cleaned_data["name"],
            self.cleaned_data["newsletter"],
            self.cleaned_data["segments"],
            self.cleaned_data["groups"],
        )

        for segment in target_segments:
            mailing = Mailing.objects.create(
                name=segment.name,
                creator_user=user,
                newsletter=self.cleaned_data["newsletter"],
                publish=False,
            )
            mailing.segments.add(segment)
