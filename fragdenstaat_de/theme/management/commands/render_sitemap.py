from pathlib import Path

from django.contrib.sitemaps import views as sitemaps_views
from django.core.management.base import BaseCommand
from django.test import RequestFactory

from fragdenstaat_de.theme.urls import sitemaps


class Command(BaseCommand):
    help = "Render sitemap"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="subcommand", required=True)
        getsections_parser = subparsers.add_parser(
            "getsections",
            help="List available sections",
        )
        getsections_parser.set_defaults(func=self.getsections)

        generate_parser = subparsers.add_parser("generate")
        generate_parser.add_argument(
            "--section",
            help="Render section (can be specified multiple times)",
            action="append",
            default=[],
        )
        generate_parser.add_argument(
            "--outdir", help="Output directory", type=Path, default=Path("/tmp/")
        )
        generate_parser.set_defaults(func=self.generate)

    def get_sections(self):
        return sitemaps.keys()

    def write_sitemap_tempfile(self, sitemap_file, sitemap_content):
        with open(sitemap_file, "w") as sitemap_out:
            sitemap_out.write(sitemap_content)
        return True

    def handle(self, *args, func, **kwargs):
        func(**kwargs)

    def getsections(self, **kwargs):
        sections = self.get_sections()

        for s in sections:
            self.stdout.write(s)

    def generate(self, section, outdir, **kwargs):
        sections = self.get_sections()

        unknown_sections = set(section) - set(sections)
        if unknown_sections:
            for unknown_section in unknown_sections:
                self.stderr.write(
                    f"Error: Section {unknown_section} does not exists. Use 'getsections' for a valid list."
                )
            return

        if not outdir.exists():
            self.stderr.write(
                f"Error: The directory {outdir} does not exists, please check/create and try again."
            )
            return

        self.stdout.write("Generating sitemap(s), this might take a while...")

        if section:
            sections = section

        for s in sections:
            self.stdout.write(s)
            factory = RequestFactory()
            sitemap_name = f"sitemap-{s}.xml"
            request = factory.get("/" + sitemap_name)
            response = sitemaps_views.sitemap(request, sitemaps, section=s)

            sitemap_dest_tmp = outdir / sitemap_name
            self.write_sitemap_tempfile(sitemap_dest_tmp, response.rendered_content)

        sitemap_name = "sitemap.xml"
        request = factory.get("/" + sitemap_name)
        response = sitemaps_views.index(request, sitemaps, sitemap_url_name="sitemaps")
        sitemap_dest_tmp = outdir / sitemap_name
        self.write_sitemap_tempfile(sitemap_dest_tmp, response.rendered_content)

        self.stdout.write("Done")
