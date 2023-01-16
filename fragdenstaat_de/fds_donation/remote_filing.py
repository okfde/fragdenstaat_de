from django.conf import settings

import requests


def backup_donation_file(file_handle, file_name):
    webdav_url = settings.DONATION_BACKUP_URL
    crdedentials = settings.DONATION_BACKUP_CREDENTIALS
    if not crdedentials or not webdav_url:
        return
    webdav_username, webdav_password = crdedentials.split(":")
    upload_to_webdav(
        file_handle, file_name, webdav_url, webdav_username, webdav_password
    )


def upload_to_webdav(
    file_handle, file_name, webdav_url, webdav_username, webdav_password
):
    """Upload a file to a WebDAV server."""
    r = requests.put(
        f"{webdav_url}/{file_name}",
        data=file_handle,
        auth=(webdav_username, webdav_password),
    )
    r.raise_for_status()
