from django.apps import AppConfig
from django.conf import settings


class FdsCmsConfig(AppConfig):
    name = "fragdenstaat_de.fds_cms"
    verbose_name = "FragDenStaat CMS"

    def ready(self):
        from froide.account import account_merged

        from . import listeners  # noqa

        account_merged.connect(merge_user)

        if settings.FDS_THUMBNAIL_ENABLE_AVIF:
            from easy_thumbnails.signals import thumbnail_created

            thumbnail_created.connect(store_as_avif)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from .models import FoiRequestListCMSPlugin

    FoiRequestListCMSPlugin.objects.filter(user=old_user).update(user=new_user)


def store_as_avif(sender, **kwargs):
    if not sender.name.endswith((".png", ".jpg", ".jpeg")):
        return

    from .tasks import generate_avif_thumbnail

    generate_avif_thumbnail.delay(sender.name, sender.storage)
