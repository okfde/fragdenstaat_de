from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from cms.admin.static_placeholder import StaticPlaceholderAdmin
from cms.extensions import PageExtensionAdmin
from cms.models.static_placeholder import StaticPlaceholder

from .models import FdsPageExtension


class FdsPageExtensionAdmin(PageExtensionAdmin):
    pass


admin.site.register(FdsPageExtension, FdsPageExtensionAdmin)


class CustomStaticPlaceholderAdmin(StaticPlaceholderAdmin):
    list_display = (
        "code",
        "edit_link",
        "dirty",
    )
    actions = ["publish"]

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:pk>/edit-placeholder/",
                self.admin_site.admin_view(self.edit_placeholder),
                name="fds_cms-staticplaceholder-edit_placeholder",
            ),
        ]
        return my_urls + urls

    def edit_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            reverse(
                "admin:fds_cms-staticplaceholder-edit_placeholder",
                kwargs={"pk": obj.pk},
            ),
            _("Edit"),
        )

    def edit_placeholder(self, request, pk):
        try:
            static_placeholder = StaticPlaceholder.objects.get(pk=pk)
        except StaticPlaceholder.DoesNotExist:
            pass

        return render(
            request,
            "fds_cms/admin/static_placeholder.html",
            {"placeholder": static_placeholder, "force_cms_render": True},
        )

    def publish(self, request, queryset):
        for obj in queryset:
            obj.publish(request, request.LANGUAGE_CODE)
        next_url = request.POST.get("next")
        if next_url:
            return redirect(next_url)


admin.site.unregister(StaticPlaceholder)
admin.site.register(StaticPlaceholder, CustomStaticPlaceholderAdmin)
