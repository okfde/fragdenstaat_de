from django.db.models import Sum, Avg
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.utils.translation import ugettext_lazy as _

from froide.helper.admin_utils import ForeignKeyFilter, make_nullfilter

from .models import DonationGift, Donor, Donation


class DonorAdmin(admin.ModelAdmin):
    list_display = (
        'email', 'first_name', 'last_name', 'city',
        'active',
        'last_donation'
    )
    list_filter = (
        'active',
        make_nullfilter('subscription', _('Dauerspende')),
        'subscription__plan__amount_year',
        'email_confirmed', 'contact_allowed',
        'become_user',
        make_nullfilter('user_id', _('has user')),
        ('user', ForeignKeyFilter),

    )
    date_hierarchy = 'first_donation'
    search_fields = ('email', 'last_name', 'first_name')
    raw_id_fields = ('user', 'subscription')


class DonationChangeList(ChangeList):
    def get_results(self, *args, **kwargs):
        ret = super().get_results(*args, **kwargs)
        q = self.result_list.aggregate(
            amount_sum=Sum('amount'),
            amount_avg=Avg('amount'),
        )
        self.amount_sum = q['amount_sum']
        self.amount_avg = round(q['amount_avg'])
        return ret


class DonationAdmin(admin.ModelAdmin):
    def get_changelist(self, request):
        return DonationChangeList

    list_display = (
        'donor', 'timestamp', 'amount', 'completed', 'received'
    )
    list_filter = (
        'completed', 'received',
        ('donor', ForeignKeyFilter),
    )
    date_hierarchy = 'timestamp'
    raw_id_fields = ('donor', 'order', 'payment')


class DonationGiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_slug')
    list_filter = ('category_slug',)
    search_fields = ('name',)


admin.site.register(Donor, DonorAdmin)
admin.site.register(Donation, DonationAdmin)
admin.site.register(DonationGift, DonationGiftAdmin)
