from django.contrib.sitemaps import views as sitemaps_views
from django.core.management.base import BaseCommand
from django.test import RequestFactory

from fragdenstaat_de.theme.urls import sitemaps


class Command(BaseCommand):
    help = "Render sitemap"

    def add_arguments(self, parser):
        parser.add_argument(
            "--section", help="Render section", default="", required=False
        )
        parser.add_argument(
            "--getsections",
            help="List available sections",
            required=False,
            action="store_true",
        )

    def handle(self, *args, **options):
        if options["getsections"]:
            for section in sitemaps:
                self.stdout.write(section)
        else:
            section = options["section"]
            factory = RequestFactory()
            if section:
                sitemap_name = "/sitemap-{}.xml".format(section)
                request = factory.get(sitemap_name)
                response = sitemaps_views.sitemap(request, sitemaps)
            else:
                sitemap_name = "/sitemap.xml"
                request = factory.get(sitemap_name)
                response = sitemaps_views.index(
                    request, sitemaps, sitemap_url_name="sitemaps"
                )
            sitemap_dest_tmp = "/tmp/{}".format(sitemap_name)
            with open(sitemap_dest_tmp, "w") as sitemap_out:
                sitemap_out.write(response.rendered_content)
