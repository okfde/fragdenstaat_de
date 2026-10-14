from django.contrib import admin
from django.contrib.sites.admin import SiteAdmin
from django.contrib.sites.models import Site

from cms.extensions import PageExtensionAdmin
from filer.admin import FolderAdmin
from filer.models import Folder

from .models import DatashowDatasetTheme, FdsPageExtension, SiteSettings


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


class SiteSettingsInline(admin.StackedInline):
    model = SiteSettings


class CmsAdminSite(SiteAdmin):
    inlines = (SiteSettingsInline,)


admin.site.unregister(Site)
admin.site.register(Site, CmsAdminSite)
