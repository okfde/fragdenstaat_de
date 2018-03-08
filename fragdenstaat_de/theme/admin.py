from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage

from tinymce.widgets import TinyMCE
from leaflet.admin import LeafletGeoAdmin

from froide.georegion.models import GeoRegion
from froide.georegion import admin as georegion_admin


class TinyMCEFlatPageAdmin(FlatPageAdmin):
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'content':
            return db_field.formfield(widget=TinyMCE(
                attrs={'cols': 80, 'rows': 20},
            ))
        return super(TinyMCEFlatPageAdmin, self).formfield_for_dbfield(db_field, **kwargs)


class GeoRegionAdmin(LeafletGeoAdmin, georegion_admin.GeoRegionAdmin):
    display_raw = True


admin.site.unregister(FlatPage)
admin.site.register(FlatPage, TinyMCEFlatPageAdmin)

admin.site.unregister(GeoRegion)
admin.site.register(GeoRegion, GeoRegionAdmin)
