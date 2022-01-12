from django.apps import AppConfig
from django.urls import reverse, NoReverseMatch
from django.utils.translation import gettext_lazy as _


class FdsCmsConfig(AppConfig):
    name = "fragdenstaat_de.fds_cms"
    verbose_name = "FragDenStaat CMS"

    def ready(self):
        from froide.account import account_merged
        from froide.helper.search import search_registry
        from . import listeners  # noqa

        account_merged.connect(merge_user)
        search_registry.register(add_search)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from .models import FoiRequestListCMSPlugin

    FoiRequestListCMSPlugin.objects.filter(user=old_user).update(user=new_user)


def add_search(request):
    try:
        return {
            "title": _("Help pages"),
            "name": "cms",
            "url": reverse("fds_cms:fds_cms-search"),
        }
    except NoReverseMatch:
        return
