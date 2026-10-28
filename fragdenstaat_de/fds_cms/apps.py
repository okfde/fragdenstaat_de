from django.apps import AppConfig

from easy_thumbnails.optimize import thumbnail_created_callback
from easy_thumbnails.signals import thumbnail_created


class FdsCmsNoConfig(AppConfig):
    name = "fragdenstaat_de.fds_cms"
    verbose_name = "FragDenStaat CMS (no config)"


class FdsCmsConfig(AppConfig):
    name = "fragdenstaat_de.fds_cms"
    verbose_name = "FragDenStaat CMS"

    def ready(self):
        from froide.account import account_merged

        from . import listeners  # noqa

        account_merged.connect(merge_user)

        thumbnail_created.disconnect(thumbnail_created_callback)
        thumbnail_created.connect(async_optimize_thumbnail)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from .models import FoiRequestListCMSPlugin

    FoiRequestListCMSPlugin.objects.filter(user=old_user).update(user=new_user)


def async_optimize_thumbnail(sender, **kwargs):
    from .tasks import optimize_thumbnail_task

    optimize_thumbnail_task.delay(
        sender.name, sender.file, sender.storage, sender.thumbnail_options
    )
