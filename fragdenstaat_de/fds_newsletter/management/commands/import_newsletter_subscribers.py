import os

from django.core.management.base import BaseCommand

from ...models import Newsletter
from ...utils import import_csv


class Command(BaseCommand):
    help = "Import newsletter subscribers from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("newsletter_id", help="ID of newsletter to import to")
        parser.add_argument("csv_file", help="CSV file to import")
        parser.add_argument("reference", help="import reference")
        parser.add_argument(
            "--email-confirmed",
            action="store_true",
            help="emails are confirmed",
        )

    def handle(self, *args, **options):
        newsletter_id = options["newsletter_id"]
        try:
            newsletter = Newsletter.objects.get(pk=newsletter_id)
        except Newsletter.DoesNotExist:
            self.stderr.write("Newsletter does not exist")
            return

        csv_file_path = options["csv_file"]
        if not os.path.exists(csv_file_path):
            self.stderr.write("CSV file does not exist")
            return
        with open(csv_file_path) as csv_file:
            import_csv(
                csv_file,
                newsletter,
                reference=options["reference"],
                email_confirmed=options["email_confirmed"],
            )
        self.stdout.write("Subscribers imported.")
