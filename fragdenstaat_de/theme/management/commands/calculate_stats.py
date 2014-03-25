from collections import Counter

import unicodecsv

from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings


class Command(BaseCommand):
    help = "Calculate stats"

    def handle(self, filename, output=None, *args, **options):
        from froide.publicbody.models import PublicBody
        from froide.foirequest.models import FoiRequest
        translation.activate(settings.LANGUAGE_CODE)

        year = 2013

        def get_status(status):
            KNOWN_STATUS = (
                'successful',
                'partially_successful',
                'refused',
            )
            MAP_STATUS = {}
            if status in KNOWN_STATUS:
                return status
            return MAP_STATUS.get(status, 'other')

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

        reader = unicodecsv.DictReader(file(filename), encoding='utf-8')
        if output == '-':
            output = self.stdout
        else:
            output = file(output, 'w')
        writer = unicodecsv.DictWriter(output,
            ('id', 'name', 'type', 'official_count', 'fds_count'), encoding='utf-8')
        writer.writeheader()
        for row in reader:
            name = row['name']
            if 'Gesamt' in name:
                continue
            is_gb = False
            if ' GB' in name:
                is_gb = True
                name = name.replace(' GB', '')
            try:
                pb = PublicBody.objects.get(
                    other_names__startswith=name + ',')
            except PublicBody.DoesNotExist:
                continue
            if is_gb:
                pbs = PublicBody.objects.filter(root=pb)
                reqs = FoiRequest.objects.filter(
                    first_message__year=year,
                    visibility__gt=0,
                    public_body__in=pbs, is_foi=True)
                stats = stats_for_queryset(reqs, u"GB: %s" % pb.name)
                name = '%s (GB)' % pb.name
                count = len(reqs)
            else:
                reqs = FoiRequest.objects.filter(first_message__year=year,
                    visibility__gt=0,
                    public_body=pb, is_foi=True)
                stats = stats_for_queryset(reqs)
                name = pb.name
                count = len(reqs)
            writer.writerow({
                'id': row['name'],
                'name': name,
                'type': 'total',
                'official_count': convert_value(row['antraege']),
                'fds_count': count
            })
            writer.writerow({
                'id': row['name'],
                'name': name,
                'type': 'gewaehrt',
                'official_count': convert_value(row['gewaehrt']),
                'fds_count': stats['successful']
            })
            writer.writerow({
                'id': row['name'],
                'name': name,
                'type': 'teilweise_gewaehrt',
                'official_count': convert_value(row['teilweise_gewaehrt']),
                'fds_count': stats['partially_successful']
            })
            writer.writerow({
                'id': row['name'],
                'name': name,
                'type': 'abgelehnt',
                'official_count': convert_value(row['abgelehnt']),
                'fds_count': stats['refused']
            })
            writer.writerow({
                'id': row['name'],
                'name': name,
                'type': 'sonstige',
                'official_count': convert_value(row['sonstige']),
                'fds_count': stats['other']
            })
