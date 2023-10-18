import logging
from io import BytesIO

from django.core.files.base import ContentFile

from celery import shared_task
from easy_thumbnails.files import generate_all_aliases
from PIL import Image

try:
    import pillow_avif  # noqa
except ImportError:
    pillow_avif = None

logger = logging.getLogger(__name__)


@shared_task
def generate_thumbnails(model, pk, field):
    instance = model._default_manager.get(pk=pk)
    fieldfile = getattr(instance, field)
    generate_all_aliases(fieldfile, include_global=True)


@shared_task
def generate_avif_thumbnail(filepath: str, storage):
    if pillow_avif is None:
        return
    logger.info("Converting %s to avif", filepath)
    avif_path = storage.path(".".join([filepath, "avif"]))
    img_file = storage.open(filepath, "rb")
    im = Image.open(img_file)
    out_file = BytesIO()
    im.save(out_file, format="avif", quality=80)
    out_file.seek(0)
    storage.save(avif_path, ContentFile(out_file.read()))
    logger.info("Done converting %s to avif", filepath)
