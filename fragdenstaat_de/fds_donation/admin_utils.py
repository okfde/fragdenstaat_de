from collections import OrderedDict

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.filters import SimpleListFilter
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from froide.helper.admin_utils import MultiFilterMixin, TaggitListFilter

from .models import DONATION_PROJECTS, TaggedDonor


class DonorProjectFilter(MultiFilterMixin, SimpleListFilter):
    title = "Project"
    parameter_name = "donations__project"
    lookup_name = "__in"

    def queryset(self, request, queryset):
        """
        don't filter donors on donation projects here,
        but in Admin.get_queryset().
        This avoids double counting donations that are
        annotated in get_queryset()
        """
        return queryset

    def lookups(self, request, model_admin):
        return DONATION_PROJECTS


class DonorTagListFilter(MultiFilterMixin, TaggitListFilter):
    tag_class = TaggedDonor
    title = "Tags"
    parameter_name = "tags__slug"
    lookup_name = "__in"


class DonorTotalAmountPerYearFilter(SimpleListFilter):
    """
    Filter donors based on their total donation amount for a specific year
    Adapted from
    https://github.com/okfde/froide/blob/9ba8e168e002be68e1fd309c9387c5c051e2fd7b/froide/helper/admin_utils.py#L499
    """

    title = _("total donation amount in year")
    parameter_name = ""
    template = "helper/forms/widgets/range_filter.html"

    def __init__(self, request, params, model, model_admin):
        super().__init__(request, params, model, model_admin)
        self.lookup_kwarg_amount = "{0}__amount".format(self.parameter_name)
        self.lookup_kwarg_year = "{0}__year".format(self.parameter_name)
        self.request = request
        self.form = self.get_form(request)

        for p in self.expected_parameters():
            if p in params:
                value = params.pop(p)
                self.used_parameters[p] = value[-1]

    def expected_parameters(self):
        return [self.lookup_kwarg_amount, self.lookup_kwarg_year]

    def lookups(self, request, model_admin):
        return ()

    def has_output(self):
        return True

    def queryset(self, request, queryset):
        if self.form.is_valid():
            validated_data = dict(self.form.cleaned_data.items())
            if validated_data:
                return self._apply_filter(queryset, validated_data)
        return queryset

    def _apply_filter(self, queryset, validated_data):
        amount_str = validated_data.get(self.lookup_kwarg_amount)
        year = validated_data.get(self.lookup_kwarg_year)
        qs = queryset

        if amount_str and year:
            # Annotate donors with total donation amount for specified year
            qs = queryset.annotate(
                amount_in_year=Sum(
                    "donations__amount",
                    filter=Q(donations__received_timestamp__year=year),
                ),
            )

            # Parse amount range: supports "min-max", "min-", "-max", or exact value
            val = amount_str.strip()
            if "-" in val:
                val = [x.strip() for x in val.split("-", 1)]
            else:
                val = [val, val]

            # Apply min/max filters based on parsed range
            if val[0]:  # Has minimum value
                try:
                    qs = qs.filter(amount_in_year__gte=float(val[0]))
                except ValueError:
                    messages.error(
                        self.request,
                        _(
                            "Invalid amount format: '{}'. Please enter a valid number."
                        ).format(val[0]),
                    )
                    return queryset

            if val[1]:  # Has maximum value
                try:
                    qs = qs.filter(amount_in_year__lte=float(val[1]))
                except ValueError:
                    messages.error(
                        self.request,
                        _(
                            "Invalid amount format: '{}'. Please enter a valid number."
                        ).format(val[1]),
                    )
                    return queryset

        return qs

    def choices(self, changelist):
        params = changelist.params.copy()
        for f in self.expected_parameters():
            params.pop(f, None)

        yield {
            "form": self.get_form(self.request),
            "params": params,
        }

    def get_form(self, request):
        form_class = self._get_form_class()
        return form_class(self.used_parameters)

    def _get_form_class(self):
        fields = self._get_form_fields()
        form_class = type(
            str("DonorAmountYearForm"), (forms.BaseForm,), {"base_fields": fields}
        )
        return form_class

    def _get_form_fields(self):
        last_year = timezone.now().year - 1

        return OrderedDict(
            (
                (
                    self.lookup_kwarg_amount,
                    forms.CharField(
                        label=_("Amount from - to:"),
                        widget=forms.TextInput(
                            attrs={
                                "type": "text",
                                "placeholder": _("e.g. 100-500, 1000-, -2000"),
                            }
                        ),
                        required=False,
                    ),
                ),
                (
                    self.lookup_kwarg_year,
                    forms.IntegerField(
                        label=_("In year:"),
                        widget=forms.NumberInput(
                            attrs={
                                "type": "number",
                                "min": "2018",
                                "max": str(last_year + 1),
                                "value": last_year,
                            }
                        ),
                        required=False,
                    ),
                ),
            )
        )


class PassiveDonationListFilter(admin.SimpleListFilter):
    title = _("Passive donation")
    parameter_name = "is_passive"

    def lookups(self, request, model_admin):
        return (
            ("0", _("active")),
            ("1", _("passive")),
        )

    def queryset(self, request, queryset):
        active_condition = Q(recurring=False) | Q(first_recurring=True)
        if self.value() == "0":
            return queryset.filter(active_condition)
        elif self.value() == "1":
            return queryset.filter(~active_condition)
        return queryset
