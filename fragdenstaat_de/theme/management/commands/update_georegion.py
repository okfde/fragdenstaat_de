from datetime import datetime
import os

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.dateparse import parse_date
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.db.models.functions import Area

from slugify import slugify
import pytz

from froide.georegion.models import GeoRegion
from froide.helper.tree_utils import get_new_child_params


def localize_date(dt):
    return pytz.timezone(settings.TIME_ZONE).localize(dt, is_dst=None)


def get_higher_ars(ars):
    if not ars.rstrip("0"):
        return ""
    while True:
        if len(ars) == 2:
            return ""
        elif len(ars) == 3:
            return ars[:2]
        elif len(ars) == 5:
            return ars[:3]
        elif len(ars) == 9:
            return ars[:5]
        elif len(ars) == 12:
            return ars[:9]
        if ars[-1] == "0":
            ars = ars[:-1]
            continue
        break
    return ""


def get_children(child):
    return GeoRegion.objects.filter(part_of=child).order_by("name")


class Command(BaseCommand):
    """
    Loads this kind of shapefile:
    https://sg.geodatenzentrum.de/web_download/vg/vg250-ew_3112/utm32s/shape/vg250-ew_3112.utm32s.shape.ebenen.zip
    """

    help = "load shapefiles to georegion"

    def add_arguments(self, parser):
        parser.add_argument("command", help="Specify command")
        parser.add_argument("path", help="Add base path")

    def handle(self, *args, **options):
        command = options["command"]
        path = options["path"]

        self.layers = [
            ("Country", "VG250_STA.shp", "country", 0),
            ("State", "VG250_LAN.shp", "state", 1),
            ("Administrative District", "VG250_RBZ.shp", "admin_district", 2),
            ("District", "VG250_KRS.shp", "district", 3),
            ("Admin Cooperation", "VG250_VWG.shp", "admin_cooperation", 4),
            ("Municipalities", "VG250_GEM.shp", "municipality", 5),
        ]

        if command == "data":
            self.load(path)
        elif command == "stats":
            self.update_stats(path)

    def update_stats(self, path):
        for name, filename, kind, level in self.layers:
            self.stdout.write("\n%s\n" % name)
            ds = self.get_ds(path, filename)
            layer = ds[0]
            count = float(len(layer))
            for i, feature in enumerate(layer):
                gf = int(feature["GF"].as_string())
                if gf < 4:
                    # Only import land masses
                    continue
                self.stdout.write("%.2f%%\r" % (i / count * 100), ending="")
                name = feature["GEN"].as_string()
                region_identifier = feature["ARS"].as_string()
                print(name, region_identifier)

                population = feature["EWZ"].as_int()
                if population is None:
                    continue
                try:
                    geo_region = GeoRegion.objects.get(
                        kind=kind, region_identifier=region_identifier
                    )
                    geo_region.population = population
                    geo_region.save(update_fields=["population"])
                except GeoRegion.DoesNotExist:
                    print("Fallback to former_ars")
                    try:
                        geo_region = GeoRegion.objects.get(
                            kind=kind,
                            # search in same district
                            region_identifier__startswith=region_identifier[:5],
                            data__former_ars__contains=region_identifier,
                        )
                        geo_region.population = population
                        geo_region.save(update_fields=["population"])
                    except GeoRegion.DoesNotExist:
                        print("Fallback to name match")
                        geo_region = GeoRegion.objects.get(
                            region_identifier__startswith=region_identifier[:5],
                            kind=kind,
                            name=name,
                        )
                        geo_region.population = population
                        geo_region.save(update_fields=["population"])

    def load(self, path):
        self.valid_date = localize_date(datetime(2021, 1, 1, 0, 0, 0))

        self.georegions = GeoRegion.objects.filter(kind__in=[x[2] for x in self.layers])

        for name, filename, kind, level in self.layers:
            self.stdout.write("\n%s\n" % name)
            self.load_by_path(path, filename, kind, level)

        GeoRegion.fix_tree()
        self.stdout.write("\nSet Gov seats\n")
        self.set_gov_seats(path, "VG250_PK.shp")

        self.stdout.write("Calculate Area\n")
        GeoRegion.objects.all().update(area=Area("geom"))

    def get_ds(self, path, filename):
        path = os.path.abspath(os.path.join(path, filename))
        return DataSource(path)

    def load_by_path(self, path, filename, kind, level):
        ds = self.get_ds(path, filename)
        mapping = LayerMapping(GeoRegion, ds, {"geom": "POLYGON"})
        self.load_bkg(ds, mapping, kind, level)

    def load_bkg(self, ds, mapping, kind, level):
        layer = ds[0]
        count = float(len(layer))
        old_ids = set(
            GeoRegion.objects.filter(kind=kind).values_list(
                "region_identifier", flat=True
            )
        )
        current_ids = set()
        for i, feature in enumerate(layer):
            self.stdout.write("%.2f%%\r" % (i / count * 100), ending="")
            region_identifier = self.load_feature(feature, mapping, kind, level)
            if region_identifier is not None:
                current_ids.add(region_identifier)

        obsolete_ids = old_ids - current_ids
        new_ids = current_ids - old_ids
        print("New IDs", len(new_ids), new_ids)
        print("Obsolete IDs", len(obsolete_ids), obsolete_ids)
        GeoRegion.objects.filter(region_identifier__in=obsolete_ids).update(
            invalid_on=self.valid_date
        )

    def load_feature(self, feature, mapping, kind, level):
        nuts = feature["NUTS"].as_string()
        gf = int(feature["GF"].as_string())
        if gf < 4:
            # Only import land masses
            return
        name = feature["GEN"].as_string()

        kind_detail = feature["BEZ"].as_string()

        nbd = feature["NBD"].as_string()
        full_name = "%s %s" % (kind_detail, name) if nbd == "ja" else name
        slug = slugify(full_name)

        geom = mapping.feature_kwargs(feature)["geom"]

        extra_data = {}

        try:
            wsk = feature["WSK"].as_string()
            if "/" in wsk:
                wsk = wsk.replace("/", "-")
            valid_on_date = parse_date(wsk)
            valid_on = localize_date(
                datetime.combine(valid_on_date, datetime.min.time())
            )
        except Exception as e:
            print(wsk)
            print(e)
            valid_on = None

        region_identifier = feature["ARS"].as_string()

        geo_region = GeoRegion.objects.filter(
            region_identifier=region_identifier, kind=kind
        ).first()
        region_exists = bool(geo_region)

        if not region_exists:
            # Try to find match:
            geo_region = GeoRegion.objects.filter(
                region_identifier__startswith=region_identifier[:5],
                kind=kind,
                name=name,
            ).first()
            if geo_region:
                extra_data["former_ars"] = geo_region.data.get("former_ars", [])
                extra_data["former_ars"].append(geo_region.region_identifier)
            region_exists = bool(geo_region)

        parent = None
        tree_params = {}
        parent_region_identifier = region_identifier
        while True:
            parent_region_identifier = get_higher_ars(parent_region_identifier)
            print(name, region_identifier, parent_region_identifier)
            if parent_region_identifier:
                try:
                    parent = self.georegions.get(
                        region_identifier=parent_region_identifier
                    )
                except GeoRegion.DoesNotExist:
                    continue
                if not region_exists:
                    parent.numchild += 1
                    parent.save(update_fields=["numchild"])
                if not region_exists or geo_region.part_of_id != parent.id:
                    tree_params = get_new_child_params(parent)
                    if GeoRegion.objects.filter(path=tree_params["path"]).exists():
                        # add_children(parent, get_children)
                        # raise Exception('Path already exists')
                        GeoRegion.fix_tree()
                if geo_region:
                    geo_region.part_of = parent
            else:
                tree_params = get_new_child_params(None)
            break

        data = {
            "slug": slug,
            "name": name,
            "kind": kind,
            "kind_detail": kind_detail,
            "level": level,
            "region_identifier": region_identifier,
            "global_identifier": nuts,
            "geom": geom,
            "area": feature.geom.area,
            "valid_on": valid_on,
            "invalid_on": None,
            "part_of": parent,
            "data": {
                "label": full_name,
                "nuts": nuts,
                "DEBKG_ID": feature["DEBKG_ID"].as_string(),
                **extra_data,
            },
        }

        if region_exists:
            GeoRegion.objects.filter(id=geo_region.id).update(**data)
        else:
            data.update(tree_params)
            GeoRegion.objects.create(**data)
        return region_identifier

    def set_gov_seats(self, path, filename):
        ds = self.get_ds(path, filename)
        mapping = LayerMapping(GeoRegion, ds, {"geom": "POINT"})
        layer = ds[0]
        count = float(len(layer))
        for i, feature in enumerate(layer):
            self.stdout.write("%.2f%%\r" % (i / count * 100), ending="")
            region_identifier = feature["RS"].as_string()
            try:
                gr = GeoRegion.objects.get(region_identifier=region_identifier)
                gr.gov_seat = mapping.feature_kwargs(feature)["geom"]
                gr.save()
            except GeoRegion.DoesNotExist:
                pass
