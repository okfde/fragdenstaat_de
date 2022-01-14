import logging

from django.apps import AppConfig
from django.urls import reverse, NoReverseMatch
from django.utils.translation import gettext_lazy as _
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

try:
    import py_ravif
except ImportError:
    logger.warn("py_ravif not found, no avif image support!")
    py_ravif = None


class FdsCmsConfig(AppConfig):
    name = "fragdenstaat_de.fds_cms"
    verbose_name = "FragDenStaat CMS"

    def ready(self):
        from froide.account import account_merged
        from froide.helper.search import search_registry
        from . import listeners  # noqa

        account_merged.connect(merge_user)
        search_registry.register(add_search)

        if py_ravif is not None:
            from easy_thumbnails.signals import thumbnail_created

            thumbnail_created.connect(store_as_avif)


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


def store_as_avif(sender, **kwargs):
    logger.info("Converting %s to avif", sender.name)
    avif_name = ".".join([sender.name, "avif"])
    img_file = sender.storage.open(sender.name, "rb")
    img_bytes = img_file.read()
    avif_bytes = py_ravif.convert_to_avif_from_bytes(img_bytes)
    sender.storage.save(avif_name, ContentFile(avif_bytes))
    logger.info("Done converting %s to avif", sender.name)
