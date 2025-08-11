from django.conf import ImproperlyConfigured, settings

import dateutil.parser
import requests

from froide.foirequest.models import FoiRequest

_session = None


def get_paperless_client():
    global _session

    if _session:
        return _session

    if not settings.PAPERLESS_API_URL:
        raise ImproperlyConfigured("PAPERLESS_API_URL not set")

    _session = requests.Session()
    _session.headers.update({"Authorization": settings.PAPERLESS_API_TOKEN})
    return _session


def get_document_data(paperless_document_id):
    client = get_paperless_client()

    DOCUMENT_URL = settings.PAPERLESS_API_URL + "/documents/{}/download/".format(
        paperless_document_id
    )
    return client.get(DOCUMENT_URL).content


def get_preview_link(paperless_document_id):
    return settings.PAPERLESS_API_URL + f"/documents/{paperless_document_id}/preview/"


def get_documents_by_correspondent(user_name):
    client = get_paperless_client()

    correspondents = get_correspondents()
    correspondent_id = next(
        (c["id"] for c in correspondents if c["name"] == user_name), None
    )

    if correspondent_id is None:
        return []

    API_URL = (
        settings.PAPERLESS_API_URL
        + f"/documents/?ordering=-added&correspondent__id={correspondent_id}&document_type__id__none={settings.PAPERLESS_UPLOADED_TYPE}"
    )

    data = client.get(API_URL).json()

    def map_doc(document):
        document["created"] = dateutil.parser.isoparse(document["created"])
        document["url"] = get_preview_link(document["id"])
        return document

    return [map_doc(doc) for doc in data["results"]]


def get_correspondents():
    client = get_paperless_client()

    API_URL = settings.PAPERLESS_API_URL + "/correspondents/"
    data = client.get(API_URL).json()

    return data["results"]


def add_tag_to_documents(paperless_document_ids: list[int], foirequest: FoiRequest):
    client = get_paperless_client()

    API_URL = settings.PAPERLESS_API_URL + "/documents/bulk_edit/"

    data = {
        "documents": paperless_document_ids,
        "method": "set_document_type",
        "parameters": {"document_type": settings.PAPERLESS_UPLOADED_TYPE},
    }

    client.post(API_URL, json=data).raise_for_status()

    data = {
        "documents": paperless_document_ids,
        "method": "modify_custom_fields",
        "parameters": {
            "add_custom_fields": {settings.PAPERLESS_REQUEST_FIELD: foirequest.pk},
            "remove_custom_fields": [],
        },
    }

    client.post(API_URL, json=data).raise_for_status()
