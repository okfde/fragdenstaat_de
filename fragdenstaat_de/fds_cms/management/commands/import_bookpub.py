import glob
import re

from django.conf import settings
from django.core.management.base import BaseCommand

from cms.api import add_plugin, create_page
from cms.models import PageContent


class Command(BaseCommand):
    help = "Import book publication"

    def add_arguments(self, parser):
        parser.add_argument("base_path", type=str)
        parser.add_argument("html_dir", type=str)

    def handle(self, *args, **options):
        html_files = glob.glob(options["html_dir"] + "/*.html")

        self.base_title = PageContent.objects.filter(
            path=options["base_path"], publisher_is_draft=True
        ).get()
        self.base_page = self.base_title.page
        html_files = sorted(html_files)
        for html_file in html_files:
            self.import_page(html_file)

    def import_page(self, html_file):
        self.stdout.write("Loading {}\n".format(html_file))
        slug = html_file.split("/")[-1].split(".")[0].split("-", 1)[-1]
        with open(html_file) as f:
            content = f.read()

        title_str = (
            re.search(r"<h1[^>]*>([^<]+)</h1>", content)
            .group(1)
            .replace("\n", " ")
            .strip()
        )
        description = (
            re.search(r"<p class=\"lead\">([^<]+)</p>", content)
            .group(1)
            .replace("\n", " ")
            .strip()
        )
        self.stdout.write('Trying to import "{}"\n'.format(title_str))
        title_path = self.base_title.path + "/" + slug

        try:
            title = PageContent.objects.get(
                path=title_path,
                publisher_is_draft=True,
                language=settings.LANGUAGE_CODE,
            )
            page = title.page
            if self.base_page != page.get_parent_page():
                raise Exception("Top page parent does not match base page")
            title.title = title_str
            title.meta_description = description
            title.save()
        except PageContent.DoesNotExist:
            page = create_page(
                title_str,
                "cms/pub_base.html",
                "de",
                parent=self.base_page,
                in_navigation=True,
                slug=slug,
                position="last-child",
                meta_description=description,
            )

        placeholder = page.placeholders.get(slot="content")
        placeholder.cmsplugin_set.all().delete()
        add_plugin(
            placeholder,
            "TextPlugin",
            "de",
            body=content,
        )
