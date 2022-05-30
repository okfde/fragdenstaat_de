import base64
import io
import json
import os

from froide.foirequest.pdf_generator import FoiRequestPDFGenerator

SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_drive_service():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    service_account_info = json.loads(
        base64.b64decode(os.environ["FDS_LEGAL_BACKUP_CREDENTIALS"]).decode("utf-8")
    )
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def make_legal_backup_for_user(user):
    from googleapiclient.http import MediaIoBaseUpload

    folder_name = "{year}-{month}-{day}:{pk}:{email}:{name}".format(
        year=user.date_left.year,
        month=user.date_left.month,
        day=user.date_left.day,
        pk=user.pk,
        email=user.email,
        name=user.get_full_name(),
    )
    file_metadata = {
        "name": folder_name,
        "parents": [os.environ["FDS_LEGAL_BACKUP_FOLDER_ID"]],
        "mimeType": "application/vnd.google-apps.folder",
    }
    drive_service = get_drive_service()
    folder = drive_service.files().create(body=file_metadata, fields="id").execute()
    folder_id = folder.get("id")

    foirequests = user.foirequest_set.all()
    for foirequest in foirequests:
        pdf_generator = FoiRequestPDFGenerator(foirequest)

        file_metadata = {
            "name": "{}-{}.pdf".format(foirequest.pk, foirequest.slug),
            "parents": [folder_id],
        }
        media = MediaIoBaseUpload(
            io.BytesIO(pdf_generator.get_pdf_bytes()),
            mimetype="application/pdf",
            resumable=True,
        )
        drive_service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()
