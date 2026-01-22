import logging
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile

from celery import shared_task
from easy_thumbnails.files import ThumbnailFile, generate_all_aliases
from easy_thumbnails.optimize import optimize_thumbnail
from PIL import Image

logger = logging.getLogger(__name__)


@shared_task
def generate_thumbnails(model, pk, field):
    instance = model._default_manager.get(pk=pk)
    fieldfile = getattr(instance, field)
    generate_all_aliases(fieldfile, include_global=True)


@shared_task
def generate_avif_thumbnail(filepath: str, storage):
    logger.info("Converting %s to avif", filepath)
    avif_path = ".".join([filepath, "avif"])
    img_file = storage.open(filepath, "rb")
    im = Image.open(img_file)
    out_file = BytesIO()
    im.save(out_file, format="avif", quality=80)
    out_file.seek(0)
    storage.save(avif_path, ContentFile(out_file.read()))
    logger.info("Done converting %s to avif", filepath)


@shared_task
def optimize_thumbnail_task(name, file, storage, thumbnail_options):
    thumbnail = ThumbnailFile(
        name=name, file=file, storage=storage, thumbnail_options=thumbnail_options
    )
    optimize_thumbnail(thumbnail)

    if settings.FDS_THUMBNAIL_ENABLE_AVIF and name.endswith((".png", ".jpg", ".jpeg")):
        generate_avif_thumbnail(name, storage)
