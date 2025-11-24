from django.forms import ModelForm

from djangocms_frontend.fields import TagTypeFormField

from .models import DesignContainerCMSPlugin


class DesignContainerForm(ModelForm):
    class Meta:
        model = DesignContainerCMSPlugin
        fields = [
            "background",
            "backdrop",
            "extra_classes",
            "container",
            "padding",
            "tag_type",
        ]

    tag_type = TagTypeFormField()
