from django.utils.translation import gettext_lazy as _

import django_filters

from froide.account.models import User
from froide.foirequest.filters import BaseFoiRequestFilterSet
from froide.helper.widgets import BootstrapSelect
from froide.organization.models import Organization
from froide.publicbody.models import PublicBody
from froide.publicbody.widgets import PublicBodySelect


class SelectRequestFilterSet(BaseFoiRequestFilterSet):
    query_fields = ["title^5", "description^3", "content"]

    publicbody = django_filters.ModelChoiceFilter(
        queryset=PublicBody._default_manager.all(),
        method="filter_publicbody",
        widget=PublicBodySelect,
        label=_("Public Body"),
    )
    user = django_filters.ModelChoiceFilter(
        queryset=User.objects.filter(is_staff=True),
        to_field_name="username",
        method="filter_user",
        widget=BootstrapSelect,
    )
    organization = django_filters.ModelChoiceFilter(
        queryset=Organization.objects.all(),
        to_field_name="slug",
        method="filter_organization",
        widget=BootstrapSelect,
        label=_("Organization"),
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # remove status filter from inherited class
        del self.filters["status"]
        del self.filters["category"]
        del self.filters["campaign"]

    class Meta:
        fields = ["q", "jurisdiction", "publicbody", "user", "organization"]
