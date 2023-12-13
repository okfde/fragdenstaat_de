from django.contrib.sitemaps import views as sitemaps_views
from django.core.management.base import BaseCommand
from django.test import RequestFactory

from fragdenstaat_de.theme.urls import sitemaps


class Command(BaseCommand):
    help = "Render sitemap"

    def add_arguments(self, parser):
        parser.add_argument("section", help="Render section", default="")

    def handle(self, *args, **options):
        section = options["section"]
        factory = RequestFactory()
        if section:
            request = factory.get("/sitemap-{}.xml".format(section))
            response = sitemaps_views.sitemap(request, sitemaps)
        else:
            request = factory.get("/sitemap.xml")
            response = sitemaps_views.index(
                request, sitemaps, sitemap_url_name="sitemaps"
            )
        self.stdout.write(response.rendered_content)
