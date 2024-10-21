from django import forms
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _

from froide.foirequest.forms.message import PostalReplyForm

from .paperless import get_document_data


class PaperlessPostalReplyForm(PostalReplyForm):
    files = None
    paperless_ids = forms.TypedMultipleChoiceField(
        label=_("Paperless Documents"),
        required=True,
        widget=forms.MultipleHiddenInput,
        coerce=int,
    )

    def __init__(self, *args, **kwargs):
        paperless_docs = kwargs.pop("paperless_docs")
        super().__init__(*args, **kwargs)
        self.fields["paperless_ids"].choices = [
            (doc["id"], doc["id"]) for doc in paperless_docs
        ]

    def clean(self):
        # Do not enforce presence of either files or text
        pass

    def save(self, user):
        message = super().save(user)
        files = []
        for paperless_id in self.cleaned_data["paperless_ids"]:
            meta_data, file_contents = get_document_data(paperless_id)
            file = ContentFile(file_contents, name=meta_data["original_file_name"])
            file.content_type = "application/pdf"
            files.append(file)

        self.save_attachments(files, message)
        return message
