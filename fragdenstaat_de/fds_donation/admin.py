from django.contrib import admin

from .models import DonationGift, Donor, Donation


class DonorAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'city',)
    list_filter = (
        'active',
        'subscription__plan', 'email_confirmed', 'contact_allowed'
    )
    search_fields = ('email', 'last_name', 'first_name')
    raw_id_fields = ('user', 'subscription')


class DonationAdmin(admin.ModelAdmin):
    list_display = (
        'donor', 'timestamp', 'amount', 'completed', 'received'
    )
    raw_id_fields = ('donor', 'order', 'payment')


class DonationGiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_slug')
    list_filter = ('category_slug',)
    search_fields = ('name',)


admin.site.register(Donor, DonorAdmin)
admin.site.register(Donation, DonationAdmin)
admin.site.register(DonationGift, DonationGiftAdmin)
