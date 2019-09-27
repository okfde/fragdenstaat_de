from django.contrib import admin

from .models import DonationGift


class DonationGiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_slug')
    list_filter = ('category_slug',)
    search_fields = ('name',)


admin.site.register(DonationGift, DonationGiftAdmin)
