import io
import logging
import re
from datetime import date, timedelta
from urllib.parse import quote_plus, urlparse
from xml.dom import minidom

from django.conf import settings

import requests

from froide.account.export import export_user_data
from froide.foirequest.pdf_generator import FoiRequestPDFGenerator

logger = logging.getLogger(__name__)


RETENTION_PERIOD = timedelta(days=365 * 3)  # 3 years


def get_webdav():
    webdav_url = settings.FDS_LEGAL_BACKUP_URL
    credentials = settings.FDS_LEGAL_BACKUP_CREDENTIALS
    if not credentials or not webdav_url:
        return
    webdav_username, webdav_password = credentials.split(":")
    if webdav_url.endswith("/"):
        webdav_url = webdav_url[:-1]
    return webdav_url, webdav_username, webdav_password


def make_legal_backup_for_user(user):
    logger.info("Creating legal backup of user %s", user.id)

    webdav_url, webdav_username, webdav_password = get_webdav()

    folder_name = "{date}:{pk}:{email}:{name}".format(
        date=user.date_left.date().isoformat(),
        pk=user.pk,
        email=user.email,
        name=user.get_full_name(),
    )
    folder_url = f"{webdav_url}/{quote_plus(folder_name)}"
    response = requests.request(
        "MKCOL", folder_url, auth=(webdav_username, webdav_password)
    )
    response.raise_for_status()

    # Add basic account info
    filename, filebytes = next(export_user_data(user))
    assert filename == "account.json"
    file_handle = io.BytesIO(filebytes)
    r = requests.put(
        f"{folder_url}/{quote_plus(filename)}",
        data=file_handle,
        auth=(webdav_username, webdav_password),
    )
    r.raise_for_status()

    foirequests = user.foirequest_set.all()
    for foirequest in foirequests:
        pdf_generator = FoiRequestPDFGenerator(foirequest)

        filename = "{}-{}.pdf".format(foirequest.pk, foirequest.slug)
        file_handle = io.BytesIO(pdf_generator.get_pdf_bytes())
        r = requests.put(
            f"{folder_url}/{quote_plus(filename)}",
            data=file_handle,
            auth=(webdav_username, webdav_password),
        )
        r.raise_for_status()

    logger.info("Created legal backup of user %s at %s", user.id, folder_url)


def cleanup_legal_backups():
    webdav_url, webdav_username, webdav_password = get_webdav()
    webdav_domain = urlparse(webdav_url).netloc

    response = requests.request(
        "PROPFIND", webdav_url, auth=(webdav_username, webdav_password)
    )
    response.raise_for_status()
    today = date.today()

    parser = minidom.parseString(response.text)

    # Two different separators used in folder names
    SPLIT_CHARS = re.compile(r"[:_]")

    for entry in parser.getElementsByTagName("d:response"):
        href = entry.getElementsByTagName("d:href")[0].firstChild.data.strip()
        # Folders always end in /
        name = href.split("/")[-2]
        try:
            cancel_date = date.fromisoformat(SPLIT_CHARS.split(name)[0])
        except ValueError:
            continue
        if cancel_date + RETENTION_PERIOD < today:
            logger.info(
                "Deleting expired legal backup %s at %s",
                name,
                href,
            )
            full_url = f"https://{webdav_domain}{href}"
            requests.delete(full_url, auth=(webdav_username, webdav_password))
