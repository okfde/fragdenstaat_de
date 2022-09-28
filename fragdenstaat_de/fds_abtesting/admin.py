from django.contrib import admin
from django.db.models import Count, DecimalField, ExpressionWrapper, F

from .models import ABTest, ABTestEvent


class ABTestAdmin(admin.ModelAdmin):
    change_form_template = "admin/fds_abtesting/ab_test_with_statistics.html"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        ab_test = ABTest.objects.filter(id=object_id).first()
        events_count = ab_test.abtestevent_set.all().count()
        ab_test_events = (
            ab_test.abtestevent_set.values("variant")
            .order_by("variant")
            .annotate(count=Count("variant"))
            .annotate(
                percentage=ExpressionWrapper(
                    F("count") * 100.0 / events_count, output_field=DecimalField()
                )
            )
        )
        extra_context["events"] = ab_test_events
        extra_context["events_count"] = events_count
        return super().change_view(
            request, object_id, form_url=form_url, extra_context=extra_context
        )


class ABTestEventAdmin(admin.ModelAdmin):
    list_display = ("variant", "ab_test")
    list_filter = ("ab_test",)


admin.site.register(ABTest, ABTestAdmin)
admin.site.register(ABTestEvent, ABTestEventAdmin)
