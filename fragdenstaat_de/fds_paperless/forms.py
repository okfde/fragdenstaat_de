import re
from datetime import date

from django import forms
from django.core.files.base import ContentFile

from froide.foirequest.forms.message import PostalReplyForm
from froide.helper.widgets import BootstrapCheckboxSelectMultiple

from .paperless import get_document_data


class PaperlessPostalReplyForm(PostalReplyForm):
    files = None
    paperless_ids = forms.MultipleChoiceField(
        label="Paperless Dokumente",
        widget=BootstrapCheckboxSelectMultiple,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        paperless_docs = kwargs.pop("paperless_docs")
        super().__init__(*args, **kwargs)
        self.fields["paperless_ids"].choices = [
            (
                doc["id"],
                "{date}: ({title}) - {content}...".format(
                    date=doc["added"],
                    title=doc["title"],
                    content=doc["content"][:100],
                ),
            )
            for doc in paperless_docs
        ]
        if paperless_docs:
            DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
            match = DATE_RE.search(paperless_docs[0]["content"])
            if match:
                self.fields["date"].initial = date(
                    int(match.group(3)), int(match.group(2)), int(match.group(1))
                )

    def clean(self):
        # Do not enforce presence of either files or text
        pass

    def save(self):
        message = super().save()
        files = []
        for paperless_id in self.cleaned_data["paperless_ids"]:
            meta_data, file_contents = get_document_data(paperless_id)
            file = ContentFile(file_contents, name=meta_data["original_file_name"])
            file.content_type = "application/pdf"
            files.append(file)

        self.save_attachments(files, message)
        return message
