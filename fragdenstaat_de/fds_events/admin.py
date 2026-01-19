from django import forms
from django.contrib import admin
from django.forms import Textarea
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from cms.api import add_plugin
from cms.toolbar.utils import get_object_edit_url

from froide.helper.widgets import TagAutocompleteWidget

from fragdenstaat_de.theme.admin import make_tag_autocomplete_admin

from .models import Event, EventTag

TAG_AUTOCOMPLETE_URL = make_tag_autocomplete_admin(
    EventTag, "fds_events-eventtag-autocomplete"
)


class EventAdminForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = "__all__"
        widgets = {
            "description": Textarea(),
            "location": Textarea(),
            "tags": TagAutocompleteWidget(autocomplete_url=TAG_AUTOCOMPLETE_URL),
        }


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    date_hierarchy = "start_date"
    list_display = ("title", "start_date", "end_date", "get_edit_link")
    list_filter = (
        "start_date",
        "end_date",
    )
    prepopulated_fields = {"slug": ("title",)}
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
