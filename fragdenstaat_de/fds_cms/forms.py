from django.forms import ModelForm

from djangocms_frontend.fields import TagTypeFormField

from .models import DesignContainerCMSPlugin


class DesignContainerForm(ModelForm):
    class Meta:
        model = DesignContainerCMSPlugin
        fields = [
            "background",
            "backdrop",
            "container",
            "padding",
            "tag_type",
            "root_attributes",
            "container_attributes",
        ]

    tag_type = TagTypeFormField()
