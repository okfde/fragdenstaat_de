import os
import csv

from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.db.models.functions import Area
from django.utils import timezone

from slugify import slugify

from froide.georegion.models import GeoRegion


class Command(BaseCommand):
    """
    Loads this kind of shapefile:
    https://sg.geodatenzentrum.de/web_download/vg/vg250-ew_3112/utm32s/shape/vg250-ew_3112.utm32s.shape.ebenen.zip
    """
    help = "load shapefiles to georegion"

    def add_arguments(self, parser):
        parser.add_argument('command', help='Command')
        parser.add_argument('path', help='Add base path')

    def handle(self, *args, **options):
        command = options['command']
        path = options['path']
        if command == 'de':
            self.load(path)
        elif command == 'berlin':
            self.load_boroughs(
                path,
                parent='Berlin',
                name_col='BEZIRK',
                ident_col='spatial_na'
            )
        elif command == 'hamburg':
            self.load_boroughs(
                path,
                parent='Hamburg',
                name_col='Bezirk_Nam',
                ident_col='Bezirk'
            )
        elif command == 'plz':
            self.load_zip(
                path
            )
        else:
            print('Bad command')

    def load_boroughs(self, path, parent=None, name_col=None, ident_col=None):
        ds = DataSource(path)
        mapping = LayerMapping(GeoRegion, ds, {'geom': 'POLYGON'})
        layer = ds[0]
        parent = GeoRegion.objects.get(kind='municipality', name=parent)
        for i, feature in enumerate(layer):
            name = feature[name_col].as_string()
            identifier = feature[ident_col].as_string()[:2]
            kind = 'borough'
            kind_detail = 'Bezirk'
            slug = slugify(name)
            geom = mapping.feature_kwargs(feature)['geom']

            region_identifier = parent.region_identifier + identifier

            GeoRegion.objects.update_or_create(
                slug=slug, kind=kind,
                defaults={
                    'name': name,
                    'kind': kind,
                    'kind_detail': kind_detail,
                    'level': 6,
                    'region_identifier': region_identifier,
                    'global_identifier': '',
                    'population': None,
                    'geom': geom,
                    'area': feature.geom.area,
                    'valid_on': None,
                    'part_of': parent
                }
            )

    def load(self, path):
        self.stdout.write("\nCountry\n")
        self.load_by_path(path, 'VG250_STA.shp', 'country', 0)

        self.stdout.write("\nState\n")
        self.load_by_path(path, 'VG250_LAN.shp', 'state', 1)

        self.stdout.write("\nAdministrative District\n")
        self.load_by_path(path, 'VG250_RBZ.shp', 'admin_district', 2)

        self.stdout.write("\nDistrict\n")
        self.load_by_path(path, 'VG250_KRS.shp', 'district', 3)

        self.stdout.write("\nAdmin Cooperation\n")
        self.load_by_path(path, 'VG250_VWG.shp', 'admin_cooperation', 4)

        self.stdout.write("\nMunicipalities\n")
        self.load_by_path(path, 'VG250_GEM.shp', 'municipality', 5)

        self.stdout.write("\nSet Gov seats\n")
        self.set_gov_seats(path, 'VG250_PK.shp')

        self.stdout.write("Create Hierarchy\n")
        self.create_hierarchy()

        self.stdout.write("Calculate Area\n")
        GeoRegion.objects.all().update(area=Area('geom'))

    def get_ds(self, path, filename):
        path = os.path.abspath(os.path.join(path, filename))
        return DataSource(path)

    def load_by_path(self, path, filename, kind, level):
        ds = self.get_ds(path, filename)
        mapping = LayerMapping(GeoRegion, ds, {'geom': 'POLYGON'})
        self.load_bkg(ds, mapping, kind, level)

    def set_gov_seats(self, path, filename):
        ds = self.get_ds(path, filename)
        mapping = LayerMapping(GeoRegion, ds, {'geom': 'POINT'})
        layer = ds[0]
        count = float(len(layer))
        for i, feature in enumerate(layer):
            self.stdout.write('%.2f%%\r' % (i / count * 100), ending='')
            region_identifier = feature['RS'].as_string()
            try:
                gr = GeoRegion.objects.get(region_identifier=region_identifier)
                gr.gov_seat = mapping.feature_kwargs(feature)['geom']
                gr.save()
            except GeoRegion.DoesNotExist:
                pass

    def load_bkg(self, ds, mapping, kind, level):
        layer = ds[0]
        count = float(len(layer))
        for i, feature in enumerate(layer):
            nuts = feature['NUTS'].as_string()
            gf = int(feature['GF'].as_string())
            if gf < 4:
                # Only import land masses
                continue
            self.stdout.write('%.2f%%\r' % (i / count * 100), ending='')
            name = feature['GEN'].as_string()
            kind_detail = feature['BEZ'].as_string()
            slug = slugify('%s %s' % (name, kind_detail))

            geom = mapping.feature_kwargs(feature)['geom']

            try:
                population = feature['EWZ'].as_int()
            except Exception:
                population = None

            GeoRegion.objects.update_or_create(slug=slug, kind=kind, defaults={
                'name': name,
                'kind': kind,
                'kind_detail': kind_detail,
                'level': level,
                'region_identifier': feature['RS'].as_string(),
                'global_identifier': nuts,
                'population': population,
                'geom': geom,
                'area': feature.geom.area,
                'valid_on': None
            })

    def load_zip(self, filename):
        path = os.path.abspath(filename)
        csv_path = os.path.join(os.path.dirname(path), 'plz_einwohner.csv')

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            population = {x['plz']: int(x['einwohner']) for x in reader}

        ds = DataSource(path)
        mapping = LayerMapping(GeoRegion, ds, {'geom': 'geometry'})
        layer = ds[0]
        count = float(len(layer))
        for i, feature in enumerate(layer):
            self.stdout.write('%.2f%%\r' % (i / count * 100), ending='')
            name = feature['plz'].as_string()
            slug = name
            geom = mapping.feature_kwargs(feature)['geom']
            GeoRegion.objects.update_or_create(
                slug=slug, kind='zipcode', defaults={
                    'name': name,
                    'geom': geom,
                    'description': feature['note'].as_string(),
                    'region_identifier': name,
                    'global_identifier': 'DE-%s' % name,
                    'area': feature.geom.area,
                    'population': population.get(name, None),
                    'level': 3,
                    'valid_on': timezone.now()
                }
            )

    def create_hierarchy(self):
        matches = [
            ('state', 'country'),
            ('district', 'state'),
            ('admin_district', 'state'),
            ('admin_cooperation', 'district'),
            ('municipality', 'district'),
            # ('zipcode', 'state'),
            # ('borough', 'municipality')
        ]
        for small, big in matches:
            for small_obj in GeoRegion.objects.filter(kind=small,
                                                          part_of__isnull=True):
                print('Trying', small_obj)
                try:
                    big_objs = GeoRegion.objects.filter(
                        kind=big,
                        geom__covers=small_obj.geom.point_on_surface
                    )
                except GEOSException:
                    big_objs = GeoRegion.objects.filter(
                        kind=big,
                        geom__covers=small_obj.geom.centroid
                    )
                if not big_objs:
                    big_objs = GeoRegion.objects.filter(
                        kind=big,
                        geom__intersects=small_obj.geom
                    )
                if len(big_objs) == 1:
                    small_obj.part_of = big_objs[0]
                    small_obj.save()
                    print(small_obj, 'assigned', big_objs[0])
                elif len(big_objs) == 0:
                    print(small_obj, "0", big)
                else:
                    big_one = [x for x in big_objs if
                                small_obj.region_identifier.startswith(
                                    x.region_identifier)]
                    if len(big_one) == 1:
                        small_obj.part_of = big_one[0]
                        small_obj.save()
                    else:
                        print(small_obj, 'too many', big_objs)
