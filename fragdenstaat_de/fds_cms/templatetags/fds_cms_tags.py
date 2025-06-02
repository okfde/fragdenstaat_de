import json
from functools import reduce

from django import template
from django.conf import settings

from cms.models import Page

from ..responsive_images import (
    ResponsiveImage,
    get_filer_thumbnails,
    get_picture_plugin_column_sizes,
    get_responsive_image,
    parse_colsizes,
)

register = template.Library()


@register.filter
def is_campaign(obj, campaign):
    return obj.reference.startswith(campaign)


def thumbnail_dims(picture_plugin, default_width=768):
    if picture_plugin.width and picture_plugin.height:
        return (picture_plugin.width, picture_plugin.height)
    elif picture_plugin.height:
        return (0, picture_plugin.height)
    elif picture_plugin.width:
        return (picture_plugin.width, 0)
    return (default_width, 0)


@register.simple_tag
def get_responsive_plugin_image(picture_plugin):
    if not picture_plugin.picture:
        return ResponsiveImage()
    if picture_plugin.width or picture_plugin.height:
        thumbnails = get_filer_thumbnails(
            picture_plugin.picture,
            sizes=[(settings.THUMBNAIL_DEFAULT_ALIAS, thumbnail_dims(picture_plugin))],
            include_original=False,
            extra_opts={"crop": "scale"},
        )
    else:
        thumbnails = get_filer_thumbnails(picture_plugin.picture)

    column_sizes = get_picture_plugin_column_sizes(picture_plugin)
    return get_responsive_image(thumbnails, column_sizes)


@register.simple_tag
def get_responsive_filer_image(filer_image, column_classes):
    if not filer_image:
        return ResponsiveImage()
    thumbnails = get_filer_thumbnails(filer_image)
    column_sizes = parse_colsizes(column_classes)
    return get_responsive_image(thumbnails, column_sizes)


@register.filter
def get_soft_root(page):
    if page.soft_root:
        return page
    soft_root = (
        page.get_ancestor_pages()
        .filter(pagecontent_set__soft_root=True)
        .reverse()
        .first()
    )
    if soft_root:
        return soft_root
    return page.get_root()


@register.simple_tag(takes_context=True)
def get_breadcrumb_ancestor(context, navigation_node):
    if navigation_node is None:
        return

    try:
        request = context["request"]
    except KeyError:
        return

    try:
        page = Page.objects.get(pk=navigation_node.id)
        ancestor = page.fdspageextension.breadcrumb_ancestor
        only_upwards = page.fdspageextension.ancestor_only_upwards
    except AttributeError:
        return

    if ancestor is None:
        return

    if only_upwards and request.current_page != page:
        return

    title = ancestor.get_title(language=request.LANGUAGE_CODE)
    url = ancestor.get_absolute_url(language=request.LANGUAGE_CODE)

    return {"title": title, "url": url}


def get_foirequest_features(foirequests, key_func, geometry_func):
    geo_groups = {}
    for foirequest in foirequests:
        coords_key = key_func(foirequest)
        if coords_key not in geo_groups:
            geo_groups[coords_key] = {
                "type": "Feature",
                "geometry": geometry_func(foirequest),
                "properties": {
                    "requests": [],
                },
            }
        geo_groups[coords_key]["properties"]["requests"].append(
            {
                "url": foirequest.get_absolute_url(),
                "title": foirequest.title,
                "public_body_name": foirequest.public_body.name,
                "status_display": foirequest.get_status_display(),
            }
        )
    return list(geo_groups.values())


@register.filter
def foirequest_geo_points(foirequests):
    all_count = foirequests.count()
    # Only include requests with public bodies that have geometry for map view
    foirequests = (
        foirequests.filter(public_body__isnull=False)
        .filter(public_body__geo__isnull=False)  # Has point geometry
        .select_related("public_body")
    )

    with_geo_count = foirequests.count()

    def geometry_func(foirequest):
        return {
            "type": "Point",
            "coordinates": [foirequest.public_body.geo.x, foirequest.public_body.geo.y],
        }

    features = get_foirequest_features(
        foirequests,
        key_func=lambda fr: fr.public_body.geo,
        geometry_func=geometry_func,
    )

    return {
        "all_count": all_count,
        "geo_count": with_geo_count,
        "missing_count": all_count - with_geo_count,
        "geojson": {
            "type": "FeatureCollection",
            "features": features,
        },
    }


@register.filter
def foirequest_geo_regions(foirequests):
    all_count = foirequests.count()
    # Only include requests with public bodies that have geometry for map view
    foirequests = (
        foirequests.filter(public_body__isnull=False)
        .filter(public_body__regions__geom__isnull=False)  # Has region with geometry
        .select_related("public_body")
        .prefetch_related("public_body__regions")
    )

    with_geo_count = foirequests.count()

    def geometry_func(foirequest):
        multi_polygon = reduce(
            lambda a, b: a | b,
            foirequest.public_body.regions.all().values_list("geom", flat=True),
        )
        return json.loads(multi_polygon.geojson)

    features = get_foirequest_features(
        foirequests,
        key_func=lambda fr: fr.public_body.id,
        geometry_func=geometry_func,
    )

    return {
        "all_count": all_count,
        "geo_count": with_geo_count,
        "missing_count": all_count - with_geo_count,
        "geojson": {
            "type": "FeatureCollection",
            "features": features,
        },
    }
