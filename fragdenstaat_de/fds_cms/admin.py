from django.contrib import admin

from cms.extensions import PageExtensionAdmin
from filer.admin import FolderAdmin
from filer.models import Folder

from .models import FdsPageExtension


class FdsPageExtensionAdmin(PageExtensionAdmin):
    pass


admin.site.register(FdsPageExtension, FdsPageExtensionAdmin)


class FdsFolderAdmin(FolderAdmin):
    owner_search_fields = ["first_name", "last_name"]


admin.site.unregister(Folder)
admin.site.register(Folder, FdsFolderAdmin)
