from django import forms
from django.contrib import admin
from django.forms import Textarea
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from cms.api import add_plugin
from cms.toolbar.utils import get_object_edit_url

from .models import Event


class EventAdminForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = "__all__"
        widgets = {"description": Textarea(), "location": Textarea()}


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    date_hierarchy = "start_date"
    list_display = ("title", "start_date", "end_date", "get_edit_link")
    list_filter = (
        "start_date",
        "end_date",
    )
    search_fields = ["title"]
    form = EventAdminForm

    def get_edit_link(self, event):
        edit_url = get_object_edit_url(event)
        return format_html(
            '<a href="{url}">{title}</a>',
            url=edit_url,
            title=_("Edit Content"),
        )

    get_edit_link.short_description = _("Content")

    def save_model(self, request, event, form, change):
        super().save_model(request, event, form, change)

        if not change:
            add_plugin(
                event.content_placeholder,
                "TextPlugin",
                language=request.LANGUAGE_CODE,
                body="<p>Content</p>",
            )
