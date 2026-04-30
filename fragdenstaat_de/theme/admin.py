from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import BadRequest, PermissionDenied
from django.db.models import Model, Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import path, reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from django_amenities.admin import AmenityAdmin as OldAmenityAdmin
from django_amenities.models import Amenity
from filer.admin.permissionadmin import PermissionAdmin as BasePermissionAdmin
from filer.models import FolderPermission
from froide_campaign.admin import InformationObjectAdmin as OldInformationObjectAdmin
from froide_campaign.models import InformationObject
from froide_crowdfunding import admin as crowdfunding_admin
from froide_crowdfunding.models import Contribution
from leaflet.admin import LeafletGeoAdmin

from froide.account.admin import UserAdmin as FroideUserAdmin
from froide.account.services import AccountService
from froide.georegion import admin as georegion_admin
from froide.georegion.models import GeoRegion
from froide.helper.admin_utils import make_choose_object_action
from froide.publicbody import admin as pb_admin
from froide.publicbody.models import ProposedPublicBody, PublicBody

from fragdenstaat_de.fds_donation.models import Donation
from fragdenstaat_de.fds_mailing.models import EmailTemplate, Mailing, MailingMessage
from fragdenstaat_de.fds_mailing.utils import SetupMailingMixin

User = get_user_model()


def execute_send_mail_template(admin, request, queryset, action_obj):
    count = queryset.count()
    if count != 1:
        admin.message_user(
            request,
            _("You can only send to one user at a time."),
            level=messages.ERROR,
        )
        return
    for user in queryset:
        action_obj.send_to_user(user)

    admin.message_user(request, _("Email was sent."), level=messages.INFO)


class UserAdmin(FroideUserAdmin):
    actions = FroideUserAdmin.actions + [
        "send_mail_template",
        "activate_journalist",
        "activate_plus",
    ]

    send_mail_template = make_choose_object_action(
        EmailTemplate, execute_send_mail_template, _("Send email via template...")
    )

    @admin.action(
        description=_("Send mailing to users..."),
        permissions=("change",),
    )
    def send_mail(self, request, queryset):
        # override UserAdmin.send_mail to create mailing instead

        if request.POST.get("subject"):
            subject = request.POST.get("subject", "")
            mailing = Mailing.objects.create(
                creator_user=request.user, name=subject, publish=False
            )
            MailingMessage.objects.bulk_create(
                [
                    MailingMessage(
                        mailing=mailing,
                        name=user.get_full_name(),
                        email=user.email,
                        user=user,
                    )
                    for user in queryset
                ]
            )
            change_url = reverse("admin:fds_mailing_mailing_change", args=[mailing.id])
            return redirect(change_url)

        return super().send_mail(request, queryset)

    @admin.action(
        description=_("Mark user as journalist (with Plus) and send mail..."),
        permissions=("change",),
    )
    def activate_journalist(self, request, queryset):
        journalist_group = Group.objects.get(name="Journalists")
        plus_group = Group.objects.get(name="FragDenStaat Plus")
        for user in queryset:
            if not user.is_trusted:
                user.is_trusted = True
                user.save(update_fields=["is_trusted"])

            user.groups.add(plus_group)  # plus group also needed for journalists

            # this also sends the proper email for journalists
            AccountService(user).add_to_group(journalist_group)

        self.message_user(request, _("Successfully executed."))

    @admin.action(
        description=_("Give user access to Plus and send mail..."),
        permissions=("change",),
    )
    def activate_plus(self, request, queryset):
        plus_group = Group.objects.get(name="FragDenStaat Plus")
        for user in queryset:
            if not user.is_trusted:
                user.is_trusted = True
                user.save(update_fields=["is_trusted"])

            # this also sends the proper email for journalists
            AccountService(user).add_to_group(plus_group)

        self.message_user(request, _("Successfully executed."))


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


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
                    (
                        contribution.order.user_email
                        if contribution.order and not contribution.user
                        else ""
                    ),
                    (
                        contribution.order.get_full_name()
                        if contribution.order and not contribution.user
                        else ""
                    ),
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
            "Prepared mailing to crowdfunding contributors with {count} recipients"
        ).format(count=count)


admin.site.unregister(Contribution)
admin.site.register(Contribution, ContributionAdmin)


def make_tag_autocomplete_admin(model: type[Model], url_name: str):
    @admin.register(model)
    class TagAutocompleteAdmin(admin.ModelAdmin):
        def get_urls(self):
            urls = super().get_urls()
            my_urls = [
                path(
                    "autocomplete/",
                    self.admin_site.admin_view(self.autocomplete),
                    name=url_name,
                ),
            ]
            return my_urls + urls

        def autocomplete(self, request):
            if not request.method == "GET":
                raise BadRequest
            if not self.has_change_permission(request):
                raise PermissionDenied

            query = request.GET.get("q", "")
            tags = []
            if query:
                tags = model.objects.filter(name__istartswith=query).values_list(
                    "name", flat=True
                )

            return JsonResponse(
                {"objects": [{"value": t, "label": t} for t in tags]}, safe=False
            )

    return reverse_lazy(f"admin:{url_name}")
