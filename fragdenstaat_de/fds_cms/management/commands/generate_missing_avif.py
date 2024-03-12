from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models.fields.files import default_storage

from fragdenstaat_de.fds_cms.tasks import generate_avif_thumbnail


def walk_folder(storage, base):
    folders, files = storage.listdir(base)

    for subfolder in folders:
        # On S3, we don't really have subfolders, so exclude "."
        if subfolder == ".":
            continue

        new_base = str(Path(base, subfolder))
        yield from walk_folder(storage, new_base)

    for file in files:
        yield Path(base, file)


class Command(BaseCommand):
    help = "Generate missing avif files for thumbnails"

    def add_arguments(self, parser):
        parser.add_argument("--base-path", type=str, default="media/thumbnails")

    def handle(self, *args, base_path, **kwargs):
        storage = default_storage
        for file in walk_folder(storage, base_path):
            if file.suffix in (".avif", ".svg"):
                continue
            if not storage.exists(str(file) + ".avif"):
                print("Generating avif for", file)
                generate_avif_thumbnail(str(file), storage)
