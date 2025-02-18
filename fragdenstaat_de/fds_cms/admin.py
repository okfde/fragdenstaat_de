from django.contrib import admin

from cms.extensions import PageExtensionAdmin
from filer.admin import FolderAdmin
from filer.models import Folder

from .models import DatashowDatasetTheme, FdsPageExtension


@admin.register(FdsPageExtension)
class FdsPageExtensionAdmin(PageExtensionAdmin):
    pass


@admin.register(DatashowDatasetTheme)
class DatashowDatasetThemeAdmin(admin.ModelAdmin):
    raw_id_fields = ["dataset"]


class FdsFolderAdmin(FolderAdmin):
    owner_search_fields = ["first_name", "last_name"]


admin.site.unregister(Folder)
admin.site.register(Folder, FdsFolderAdmin)
