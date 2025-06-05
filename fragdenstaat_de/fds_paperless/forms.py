from django import forms
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _

from froide.foirequest.forms.message import PostalReplyForm
from froide.helper.storage import make_filename

from .paperless import get_document_data


class PaperlessPostalReplyForm(PostalReplyForm):
    sender = forms.CharField(required=False, max_length=250, widget=forms.HiddenInput)
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
            (doc["id"], doc["title"]) for doc in paperless_docs
        ]
        self.paperless_docs = paperless_docs

    def clean(self):
        # Do not enforce presence of either files or text
        pass

    def get_file_name(self, doc_id):
        return next(
            make_filename(doc["title"] + ".pdf")
            for doc in self.paperless_docs
            if doc["id"] == doc_id
        )

    def save(self, user):
        message = super().save(user)
        files = []
        for paperless_id in self.cleaned_data["paperless_ids"]:
            file_contents = get_document_data(paperless_id)
            file = ContentFile(file_contents, name=self.get_file_name(paperless_id))
            file.content_type = "application/pdf"
            files.append(file)

        self.save_attachments(files, message)
        return message
