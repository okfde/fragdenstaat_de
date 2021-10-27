import csv
from collections import Counter

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Calculate stats"

    def add_arguments(self, parser):
        parser.add_argument("output")

    def handle(self, **options):
        output = options["output"]
        from froide.publicbody.models import PublicBody
        from froide.foirequest.models import FoiRequest

        year = 2015

        def get_status(status):
            KNOWN_STATUS = (
                "successful",
                "partially_successful",
                "refused",
            )
            MAP_STATUS = {}
            if status in KNOWN_STATUS:
                return status
            return MAP_STATUS.get(status, "other")

        def convert_value(val):
            if not val:
                return 0
            else:
                return int(val)

        def stats_for_queryset(qs, key=None):
            status_counter = Counter()
            for r in qs:
                arg = key
                if arg is None:
                    arg = r.public_body.name
                status_counter[get_status(r.status)] += 1
            return status_counter

        output = open(output, "w")
        writer = csv.DictWriter(
            output, ("name", "gb", "year", "total_count"), encoding="utf-8"
        )
        writer.writeheader()

        short_names = [
            "BK",
            "BMAS",
            "AA",
            "BMI",
            "BMJV",
            "BMF",
            "BMWi",
            "BMEL",
            "BMVg",
            "BMFSFJ",
            "BMG",
            "BMVI",
            "BMUB",
            "BMBF",
            "BKM",
            "BMZ",
            "BPA",
            "BPräsA",
            "BT",
            "BR",
            "BBank",
            "BfDI",
            "BRH",
            "BVerfG",
        ]

        for year in range(2011, 2018):
            for short_name in short_names:
                print(short_name)
                try:
                    root_pb = PublicBody.objects.get(
                        jurisdiction_id=1, other_names__contains="%s," % short_name
                    )
                except PublicBody.DoesNotExist:
                    print("missing")
                    continue
                root_count = root_pb.foirequest_set.filter(
                    first_message__year=year, is_foi=True
                ).count()
                pbs = PublicBody.objects.filter(root=root_pb)
                qs = FoiRequest.objects.filter(
                    first_message__year=year, public_body__in=pbs, is_foi=True
                )
                total_count = len(list(qs))
                writer.writerow(
                    {
                        "name": short_name,
                        "year": year,
                        "gb": "True",
                        "total_count": total_count,
                    }
                )
                writer.writerow(
                    {
                        "name": short_name,
                        "year": year,
                        "gb": "False",
                        "total_count": root_count,
                    }
                )
