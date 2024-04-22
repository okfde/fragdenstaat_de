import os

from django.conf import settings

import requests


def backup_donation_file(file_handle, file_name):
    webdav_url = settings.DONATION_BACKUP_URL
    crdedentials = settings.DONATION_BACKUP_CREDENTIALS
    if not crdedentials or not webdav_url:
        return
    webdav_username, webdav_password = crdedentials.split(":")
    count = 0
    original_file_stem, orignal_file_ext = os.path.splitext(file_name)
    while webdav_file_exists(file_name, webdav_url, webdav_username, webdav_password):
        count += 1
        file_name = f"{original_file_stem}-{count}.{orignal_file_ext}"
    upload_to_webdav(
        file_handle, file_name, webdav_url, webdav_username, webdav_password
    )


def webdav_file_exists(
    file_name: str, webdav_url: str, webdav_username: str, webdav_password: str
) -> bool:
    r = requests.get(
        f"{webdav_url}/{file_name}",
        auth=(webdav_username, webdav_password),
    )
    if r.status_code not in [200, 404]:
        r.raise_for_status()
    return r.status_code == 200


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
