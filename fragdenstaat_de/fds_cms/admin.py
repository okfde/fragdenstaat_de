from django.contrib import admin
from cms.extensions import PageExtensionAdmin

from .models import FdsPageExtension


class FdsPageExtensionAdmin(PageExtensionAdmin):
    pass


admin.site.register(FdsPageExtension, FdsPageExtensionAdmin)
