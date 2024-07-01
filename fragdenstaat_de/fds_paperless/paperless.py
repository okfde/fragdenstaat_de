from datetime import timedelta

from django.conf import settings
from django.utils import timezone

import requests


def get_paperless_client():
    session = requests.Session()
    session.headers.update({"Authorization": settings.PAPERLESS_API_TOKEN})
    return session


def get_document_data(paperless_document_id):
    API_URL = settings.PAPERLESS_API_URL + "/documents/{}/".format(
        paperless_document_id
    )
    client = get_paperless_client()
    meta_data = client.get(API_URL).json()

    DOCUMENT_URL = settings.PAPERLESS_API_URL + "/documents/{}/download/".format(
        paperless_document_id
    )
    file_data = client.get(DOCUMENT_URL).content

    return meta_data, file_data


def list_documents():
    client = get_paperless_client()
    last_week = timezone.now() - timedelta(days=7)
    API_URL = settings.PAPERLESS_API_URL + "/documents/?added__date__gt={}".format(
        last_week.date()
    )
    data = client.get(API_URL).json()
    return list(reversed(data["results"]))
