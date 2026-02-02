import zoneinfo
from datetime import datetime

from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand
from django.utils import timezone

from slugify import slugify

from froide.georegion.models import GeoRegion
from froide.helper.tree_utils import get_new_child_params


def get_higher_ars(ars):
    if not ars.rstrip("0"):
        return ""
    ars = ars.rstrip("0")
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
    https://gdz.bkg.bund.de/index.php/default/verwaltungsgebiete-1-25-000-stand-31-12-vg25.html
    """

    help = "load shapefiles to georegion"

    def add_arguments(self, parser):
        parser.add_argument("command", help="Specify command")
        parser.add_argument("path", help="Add base path")

    def handle(self, *args, **options):
        command = options["command"]
        path = options["path"]

        self.layers = [
            ("Country", "vg25_sta", "country", 0),
            ("State", "vg25_lan", "state", 1),
            ("Administrative District", "vg25_rbz", "admin_district", 2),
            ("District", "vg25_krs", "district", 3),
            ("Admin Cooperation", "vg25_vwg", "admin_cooperation", 4),
            ("Municipalities", "vg25_gem", "municipality", 5),
        ]

        if command == "data":
            self.load(path)
        elif command == "stats":
            self.update_stats(path)

    def update_stats(self, path):
        import geopandas as gpd

        for name, layer_name, kind, _level in self.layers:
            self.stdout.write("\n%s\n" % name)
            layer = gpd.read_file(path, layer=layer_name)
            count = float(len(layer))
            for i, feature in enumerate(layer):
                gf = int(feature["GF"])
                if gf < 4:
                    # Only import land masses
                    continue
                self.stdout.write("%.2f%%\r" % (i / count * 100), ending="")
                name = feature["GEN"]
                region_identifier = feature["ARS"]
                print(name, region_identifier)

                population = feature["EWZ"]
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
        import geopandas as gpd

        self.valid_date = datetime(
            2024, 12, 31, 0, 0, 0, tzinfo=timezone.get_current_timezone()
        )

        self.georegions = GeoRegion.objects.filter(kind__in=[x[2] for x in self.layers])

        for label, layer_name, region_kind, level in self.layers:
            self.stdout.write(f"\n{label}\n")
            layer = gpd.read_file(path, layer=layer_name)
            layer = layer.to_crs("EPSG:4326")

            layer = layer[(layer["BSG"] == 1) & (layer["GF"].isin([4, 9]))]
            self.load_bkg(layer, region_kind, level)

        GeoRegion.fix_tree()

    def load_bkg(self, layer, kind, level):
        count = float(len(layer))
        old_ids = set(
            GeoRegion.objects.filter(kind=kind).values_list(
                "region_identifier", flat=True
            )
        )
        old_ids = {r.ljust(12, "0") for r in old_ids}
        current_ids = set()
        for i, (_index, feature) in enumerate(layer.iterrows()):
            self.stdout.write("%.2f%%\r" % (i / count * 100), ending="")
            region_identifier = self.load_feature(feature, kind, level)
            if region_identifier is not None:
                current_ids.add(region_identifier)

        obsolete_ids = old_ids - current_ids
        new_ids = current_ids - old_ids
        print("New IDs", len(new_ids), new_ids)
        print("Obsolete IDs", len(obsolete_ids), obsolete_ids)
        GeoRegion.objects.filter(region_identifier__in=obsolete_ids).update(
            invalid_on=self.valid_date
        )

    def load_feature(self, feature, kind, level):
        nuts = str(feature["NUTS"])
        name = feature["GEN"]

        kind_detail = feature["BEZ"]

        nbd = feature["NBD"]
        full_name = "%s %s" % (kind_detail, name) if nbd == "ja" else name
        slug = slugify(full_name)

        geom = feature["geometry"]

        extra_data = {}
        berlin = zoneinfo.ZoneInfo("Europe/Berlin")
        valid_on = feature["WSK"].to_pydatetime().astimezone(berlin)

        region_identifier = feature["ARS"].ljust(12, "0")

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
            parent_region_identifier = get_higher_ars(parent_region_identifier).ljust(
                12, "0"
            )
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

        dlm_id = feature["OBJID"] if "OBJID" in feature else feature["DLM_ID"]

        data = {
            "slug": slug,
            "name": name,
            "kind": kind,
            "kind_detail": kind_detail,
            "level": level,
            "region_identifier": region_identifier,
            "global_identifier": nuts,
            "geom": GEOSGeometry(geom.wkt, srid=4326),
            "area": geom.area,
            "valid_on": valid_on,
            "invalid_on": None,
            "part_of": parent,
            "data": {
                "label": full_name,
                "nuts": nuts,
                "DEBKG_ID": dlm_id,
                **extra_data,
            },
        }

        if region_exists:
            GeoRegion.objects.filter(id=geo_region.id).update(**data)
        else:
            data.update(tree_params)
            GeoRegion.objects.create(**data)
        return region_identifier
