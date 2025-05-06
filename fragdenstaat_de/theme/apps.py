from datetime import timedelta

from django.apps import AppConfig
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ThemeConfig(AppConfig):
    name = "fragdenstaat_de.theme"
    verbose_name = _("FragDenStaat")

    def ready(self):
        from froide.account import account_future_canceled
        from froide.account.registries import user_extra_registry

        from fragdenstaat_de.fds_mailing import gather_mailing_preview_context
        from fragdenstaat_de.fds_newsletter import tag_subscriber

        from .forms import SignupUserCheckExtra

        user_extra_registry.register("registration", SignupUserCheckExtra())
        account_future_canceled.connect(start_legal_backup)
        tag_subscriber.connect(tag_subscriber_froide_user)
        gather_mailing_preview_context.connect(provide_foirequest_mailing_context)


def start_legal_backup(sender, **kwargs):
    from .tasks import make_legal_backup

    make_legal_backup.delay(sender.id)


def tag_subscriber_froide_user(sender, email=None, **kwargs):
    from froide.account.models import User
    from froide.campaign.models import Campaign

    user = (
        User.objects.filter(email_deterministic=email)
        .annotate(last_request=Max("foirequest__created_at"))
        .first()
    )
    if not user:
        return

    add_tags = set()
    remove_tags = set()

    YEAR = timedelta(days=365)

    if user.is_trusted:
        add_tags.add("user:trusted")
    else:
        remove_tags.add("user:trusted")

    if user.last_request:
        remove_tags.add("foirequest:no_requests")
        add_tags.add("foirequest:has_requests")
        if user.last_request > timezone.now() - YEAR:
            add_tags.add("foirequest:active")
        else:
            remove_tags.add("foirequest:active")
    else:
        add_tags.add("foirequest:no_requests")

    campaigns = Campaign.objects.filter(foirequest__user=user).values_list(
        "slug", flat=True
    )
    add_tags |= {f"campaign:{slug}" for slug in campaigns}
    return add_tags, remove_tags


def provide_foirequest_mailing_context(sender, **kwargs):
    from froide.foirequest.models import FoiRequest
    from froide.publicbody.models import PublicBody

    from fragdenstaat_de.fds_mailing import MailingPreviewContextProvider

    def get_foirequest_info(value, request):
        if value == "no_foirequest":
            return
        foirequest = FoiRequest(
            title=_("Example foirequest title"),
            description=_("Example foirequest description"),
            public_body=PublicBody.objects.first(),
            user=request.user,
        )
        return {
            "foirequest": foirequest,
        }

    return MailingPreviewContextProvider(
        "foirequest",
        {
            "no_foirequest": _("---"),
            "foirequest": _("Foirequest"),
        },
        get_foirequest_info,
    )
