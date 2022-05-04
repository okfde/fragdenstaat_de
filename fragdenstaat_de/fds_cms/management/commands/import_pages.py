import csv

from django.core.management.base import BaseCommand

from cms.api import add_plugin, create_page
from cms.models import Title
from slugify import slugify


class Command(BaseCommand):
    help = "Import pages"

    def add_arguments(self, parser):
        parser.add_argument("base_path", type=str)
        parser.add_argument("file", type=str)

    def handle(self, *args, **options):
        reader = csv.DictReader(open(options["file"]))

        self.base_title = Title.objects.filter(
            path=options["base_path"], publisher_is_draft=True
        ).get()
        self.base_page = self.base_title.page
        for line in reader:
            self.import_page(line)

    def import_page(self, row):
        top_title_str = row["Titel der Oberseite"]
        title_str = row["Titel"]
        if not title_str:
            return
        self.stdout.write('Trying to import "{}"\n'.format(title_str))
        menu_title_str = row["Menütitel (optional)"]
        description = row["Beschreibung"]

        top_title = Title.objects.filter(
            title=top_title_str, publisher_is_draft=True
        ).get()
        top_page = top_title.page
        if self.base_page != top_page.get_parent_page():
            raise Exception("Top page parent does not match base page")

        try:
            titles = Title.objects.filter(title=title_str, publisher_is_draft=True)
            right_titles = [t for t in titles if t.page.get_parent_page() == top_page]
            if right_titles:
                # title exists with correct parent, we are done
                return
            # Wrong parent, create title
        except Title.DoesNotExist:
            pass

        kwargs = {}
        if menu_title_str:
            kwargs["menu_title"] = menu_title_str
        if description:
            kwargs["meta_description"] = description
        page = create_page(
            title_str,
            "cms/help_base.html",
            "de",
            parent=top_page,
            in_navigation=True,
            slug=slugify(
                title_str, replacements=[["ä", "ae"], ["ö", "oe"], ["ü", "ue"]]
            ),
            position="last-child",
            **kwargs
        )
        placeholder = page.placeholders.get(slot="content")
        add_plugin(
            placeholder,
            "TextPlugin",
            "de",
            body="""<h2>{}</h2><p>Inhalt folgt...</p>""".format(title_str),
        )
