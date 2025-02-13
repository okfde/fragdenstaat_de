from django.conf import ImproperlyConfigured, settings

import dateutil.parser
import requests


def get_paperless_client():
    if not settings.PAPERLESS_API_URL:
        raise ImproperlyConfigured("PAPERLESS_API_URL not set")

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


def list_documents(page=1):
    client = get_paperless_client()

    API_URL = (
        settings.PAPERLESS_API_URL
        + "/documents/?page={}&page_size=12&ordering=-created&truncate_content=true".format(
            page
        )
    )

    data = client.get(API_URL).json()

    def map_doc(document):
        document["created"] = dateutil.parser.isoparse(document["created"])
        document["url"] = get_preview_link(document["id"])
        return document

    return [map_doc(doc) for doc in data["results"]]


def get_documents(paperless_document_ids: list[int]):
    client = get_paperless_client()

    docs = []
    for paperless_document_id in paperless_document_ids:
        API_URL = settings.PAPERLESS_API_URL + "/documents/{}/".format(
            paperless_document_id
        )
        docs.append(client.get(API_URL).json())
    return docs


def get_preview_link(paperless_document_id):
    return settings.PAPERLESS_API_URL + f"/documents/{paperless_document_id}/preview/"


def get_thumbnail(paperless_document_id: int) -> tuple[str, bytes]:
    client = get_paperless_client()
    THUMBNAIL_URL = (
        settings.PAPERLESS_API_URL + f"/documents/{paperless_document_id}/thumb/"
    )
    thumbnail = client.get(THUMBNAIL_URL)
    return thumbnail.headers.get("Content-Type", ""), thumbnail.content


def add_tag_to_documents(paperless_document_ids: list[int]):
    client = get_paperless_client()

    API_URL = settings.PAPERLESS_API_URL + "/documents/bulk_edit/"

    data = {
        "documents": paperless_document_ids,
        "method": "set_document_type",
        "parameters": {"document_type": settings.PAPERLESS_UPLOADED_TYPE},
    }

    client.post(API_URL, json=data)
