from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage

from tinymce.widgets import TinyMCE
from leaflet.admin import LeafletGeoAdmin

from froide.georegion.models import GeoRegion
from froide.georegion import admin as georegion_admin

from froide.publicbody.models import PublicBody, ProposedPublicBody
from froide.publicbody import admin as pb_admin

from django_amenities.models import Amenity
from django_amenities.admin import AmenityAdmin as OldAmenityAdmin


class TinyMCEFlatPageAdmin(FlatPageAdmin):
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'content':
            return db_field.formfield(widget=TinyMCE(
                attrs={'cols': 80, 'rows': 20},
            ))
        return super(TinyMCEFlatPageAdmin, self).formfield_for_dbfield(db_field, **kwargs)


class GeoRegionAdmin(georegion_admin.GeoRegionMixin, LeafletGeoAdmin):
    display_raw = True


class PublicBodyAdmin(pb_admin.PublicBodyAdminMixin, LeafletGeoAdmin):
    display_raw = True


class ProposedPublicBodyAdmin(pb_admin.ProposedPublicBodyAdminMixin, LeafletGeoAdmin):
    display_raw = True


class AmenityAdmin(LeafletGeoAdmin, OldAmenityAdmin):
    display_raw = True


admin.site.unregister(FlatPage)
admin.site.register(FlatPage, TinyMCEFlatPageAdmin)

admin.site.unregister(GeoRegion)
admin.site.register(GeoRegion, GeoRegionAdmin)

admin.site.unregister(PublicBody)
admin.site.register(PublicBody, PublicBodyAdmin)

admin.site.unregister(ProposedPublicBody)
admin.site.register(ProposedPublicBody, ProposedPublicBodyAdmin)

admin.site.unregister(Amenity)
admin.site.register(Amenity, AmenityAdmin)
