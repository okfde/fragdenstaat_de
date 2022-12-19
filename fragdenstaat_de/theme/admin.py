from django.contrib import admin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_amenities.admin import AmenityAdmin as OldAmenityAdmin
from django_amenities.models import Amenity
from filer.admin.permissionadmin import PermissionAdmin as BasePermissionAdmin
from filer.models import FolderPermission
from fragdenstaat_de.fds_donation.models import Donation
from fragdenstaat_de.fds_mailing.models import MailingMessage
from fragdenstaat_de.fds_mailing.utils import SetupMailingMixin
from froide_campaign.admin import InformationObjectAdmin as OldInformationObjectAdmin
from froide_campaign.models import InformationObject
from froide_crowdfunding import admin as crowdfunding_admin
from froide_crowdfunding.models import Contribution
from leaflet.admin import LeafletGeoAdmin

from froide.georegion import admin as georegion_admin
from froide.georegion.models import GeoRegion
from froide.publicbody import admin as pb_admin
from froide.publicbody.models import ProposedPublicBody, PublicBody


class GeoRegionAdmin(georegion_admin.GeoRegionMixin, LeafletGeoAdmin):
    display_raw = True


class PublicBodyAdmin(pb_admin.PublicBodyAdminMixin, LeafletGeoAdmin):
    display_raw = True


class ProposedPublicBodyAdmin(pb_admin.ProposedPublicBodyAdminMixin, LeafletGeoAdmin):
    display_raw = True


class AmenityAdmin(LeafletGeoAdmin, OldAmenityAdmin):
    display_raw = True


class InformationObjectAdmin(LeafletGeoAdmin, OldInformationObjectAdmin):
    display_raw = True


class PermissionAdmin(BasePermissionAdmin):
    # No user in list_filter or admin page doesn't load
    list_filter = []


admin.site.unregister(GeoRegion)
admin.site.register(GeoRegion, GeoRegionAdmin)

admin.site.unregister(PublicBody)
admin.site.register(PublicBody, PublicBodyAdmin)

admin.site.unregister(ProposedPublicBody)
admin.site.register(ProposedPublicBody, ProposedPublicBodyAdmin)

admin.site.unregister(Amenity)
admin.site.register(Amenity, AmenityAdmin)

admin.site.unregister(InformationObject)
admin.site.register(InformationObject, InformationObjectAdmin)

admin.site.unregister(FolderPermission)
admin.site.register(FolderPermission, PermissionAdmin)


# Monkey patch Crowdfunding contribution admin to support sending mailings
# to contributors
class ContributionAdmin(SetupMailingMixin, crowdfunding_admin.ContributionAdmin):
    actions = list(crowdfunding_admin.ContributionAdmin.actions) + list(
        SetupMailingMixin.actions
    )

    def setup_mailing_messages(self, mailing, queryset):
        queryset = queryset.filter(
            Q(user__is_active=True) | ~Q(order__user_email="")
        ).select_related("user", "order")

        already = set()
        messages = []
        for contribution in queryset:
            email = (
                contribution.order.user_email
                if contribution.user is None
                else contribution.user.email
            )
            if email in already:
                continue
            already.add(email)
            donor = None
            if contribution.order:
                donation = Donation.objects.filter(order=contribution.order).first()
                if donation:
                    donor = donation.donor
            messages.append(
                (
                    contribution.user,
                    contribution.order.user_email
                    if contribution.order and not contribution.user
                    else "",
                    contribution.order.get_full_name()
                    if contribution.order and not contribution.user
                    else "",
                    donor,
                )
            )

        count = queryset.count()
        MailingMessage.objects.bulk_create(
            [
                MailingMessage(
                    mailing_id=mailing.id,
                    user=user,
                    name=name,
                    email=email,
                    donor=donor,
                )
                for user, email, name, donor in messages
            ]
        )

        return _(
            "Prepared mailing to crowdfunding contributors " "with {count} recipients"
        ).format(count=count)


admin.site.unregister(Contribution)
admin.site.register(Contribution, ContributionAdmin)
