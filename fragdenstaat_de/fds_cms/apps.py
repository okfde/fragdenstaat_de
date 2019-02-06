from django.apps import AppConfig


class FdsCmsConfig(AppConfig):
    name = 'fragdenstaat_de.fds_cms'
    verbose_name = 'FragDenStaat CMS'

    def ready(self):
        from froide.account import account_merged

        account_merged.connect(merge_user)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from .models import FoiRequestListCMSPlugin

    FoiRequestListCMSPlugin.objects.filter(user=old_user).update(
        user=new_user
    )
