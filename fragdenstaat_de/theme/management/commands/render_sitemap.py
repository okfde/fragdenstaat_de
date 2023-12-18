import os

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
        parser.add_argument(
            "--outdir", help="Output directory", required=False, default="/tmp/"
        )

    def get_sections(self):
        sections = []
        for section in sitemaps:
            sections.append(section)
        return sections

    def write_sitemap_tempfile(self, sitemap_file, sitemap_content):
        with open(sitemap_file, "w") as sitemap_out:
            sitemap_out.write(sitemap_content)
        return True

    def handle(self, *args, **options):
        sections = []
        sections = self.get_sections()
        section = options["section"]
        outdir = options["outdir"]

        if options["getsections"]:
            for s in sections:
                self.stdout.write(s)
            exit()

        if section and section not in sections:
            self.stderr.write(
                "Error: Section {} does not exists. Use '--getsections' for a valid list.".format(
                    section
                )
            )
            exit()

        if not os.path.isdir(outdir):
            self.stderr.write(
                "Error: The directory {} does not exists, please check/create and try again.".format(
                    outdir
                )
            )
            exit()

        self.stdout.write("Generating sitemap(s), this might take a while...")

        if section:
            sections.clear()
            sections = [section]

        for s in sections:
            self.stdout.write("{}".format(s))
            factory = RequestFactory()
            sitemap_name = "/sitemap-{}.xml".format(s)
            request = factory.get(sitemap_name)
            response = sitemaps_views.sitemap(request, sitemaps, section=s)

            sitemap_dest_tmp = "{}/{}".format(outdir, sitemap_name)
            self.write_sitemap_tempfile(sitemap_dest_tmp, response.rendered_content)

        sitemap_name = "/sitemap.xml"
        request = factory.get(sitemap_name)
        response = sitemaps_views.index(request, sitemaps, sitemap_url_name="sitemaps")
        sitemap_dest_tmp = "{}/{}".format(outdir, sitemap_name)
        self.write_sitemap_tempfile(sitemap_dest_tmp, response.rendered_content)

        self.stdout.write("Done")
