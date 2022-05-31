import base64
import io
import json
import logging
import os
from datetime import date, timedelta

from froide.foirequest.pdf_generator import FoiRequestPDFGenerator

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]

RETENTION_PERIOD = timedelta(days=365 * 3)  # 3 years


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

    logger.info("Creating legal backup of user %s", user.id)

    folder_name = "{date}:{pk}:{email}:{name}".format(
        date=user.date_left.date().isoformat(),
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
    logger.info("Created legal backup of user %s with drive id %s", user.id, folder_id)


def cleanup_legal_backups():
    parent = os.environ["FDS_LEGAL_BACKUP_FOLDER_ID"]
    drive_service = get_drive_service()
    page_token = None
    deleted_any = False

    while True:
        response = (
            drive_service.files()
            .list(
                q="mimeType='application/vnd.google-apps.folder' and '{parent}' in parents".format(
                    parent=parent
                ),
                fields="nextPageToken, files(id, name)",
                pageToken=page_token,
            )
            .execute()
        )
        today = date.today()
        for folder in response.get("files", []):
            name = folder["name"]
            cancel_date = date.fromisoformat(name.split(":")[0])
            if cancel_date + RETENTION_PERIOD < today:
                logger.info(
                    "Deleting expired legal backup %s with drive id %s",
                    name,
                    folder["id"],
                )
                drive_service.files().delete(fileId=folder["id"]).execute()
                deleted_any = True

        page_token = response.get("nextPageToken", None)
        if page_token is None:
            break

    if deleted_any:
        drive_service.files().emptyTrash().execute()
