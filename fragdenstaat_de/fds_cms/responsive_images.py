from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from django.conf import settings

from easy_thumbnails.files import get_thumbnailer


@dataclass
class ResponsiveImageThumbnail:
    url: str
    size: Tuple[int, int]
    alias: str


@dataclass
class ResponsiveImageSourceTypes:
    mime_type: str
    extension: str


@dataclass
class ResponsiveImageSource:
    mime_type: str
    srcset: str


@dataclass
class ResponsiveImage:
    src: str = ""
    srcset: str = ""
    sizes: str = ""
    sources: List[ResponsiveImageSource] = field(default_factory=list)


def get_extra_source_types() -> List[ResponsiveImageSourceTypes]:
    source_types = []
    if settings.FDS_THUMBNAIL_ENABLE_AVIF:
        source_types.append(
            ResponsiveImageSourceTypes(mime_type="image/avif", extension=".avif")
        )
    return source_types


def get_srcsets(
    source_types: List[ResponsiveImageSourceTypes],
    thumbnails: List[ResponsiveImageThumbnail],
) -> Dict[str, str]:
    srcsets = {}
    for source_type in source_types:
        srcsets[source_type.mime_type] = ", ".join(
            [
                "{url}{extension} {width}w".format(
                    url=thumbnail.url,
                    extension=source_type.extension,
                    width=thumbnail.size[0],
                )
                for thumbnail in thumbnails
            ]
        )

    return srcsets


BS_BREAKPOINTS = (
    # name, breakpoint, max-width container
    ("xs", 576, None),
    ("sm", 576, 540),
    ("md", 768, 780),  # changed from original Bootstrap 720px!
    ("lg", 992, 960),
    ("xl", 1200, 1140),
    ("xxl", 1400, 1320),
)
COL_BASE = 12
PADDING = "1.5rem"
ColumnSizes = Dict[str, int]


def parse_colsizes(colsizes) -> ColumnSizes:
    colsizes = colsizes.split()
    result = {}
    for colsize in colsizes:
        parts = colsize.split("-")
        if len(parts) == 2:
            key = "xs"
            count = int(parts[1])
        elif len(parts) == 3:
            key = parts[1]
            count = int(parts[2])
        else:
            continue
        result[key] = count
    return result


def find_parent_plugin_size(instance, levels=2) -> Optional[ColumnSizes]:
    num_levels = 0
    current_instance = instance
    has_container = False
    while num_levels < levels:
        parent = current_instance.parent
        if not parent:
            break
        if "container" in parent.plugin_type.lower():
            has_container = True
        elif parent.plugin_type == "GridColumnPlugin":
            parent_model, _parent_instance = parent.get_plugin_instance()

            return {
                name: parent_model.config.get("{}_col".format(name))
                for name, _, _ in BS_BREAKPOINTS
                if parent_model.config.get("{}_col".format(name))
            }

        num_levels += 1
        current_instance = parent
    if has_container:
        return {name: COL_BASE for name, _, _ in BS_BREAKPOINTS}
    return None


def get_picture_plugin_column_sizes(instance) -> ColumnSizes:
    attrs = instance.attributes or {}
    colsizes = attrs.get("data-colsizes")
    if colsizes:
        return parse_colsizes(colsizes)
    parent_size = find_parent_plugin_size(instance)
    if parent_size:
        return parent_size
    return {}


def fill_colsizes_upward(colsizes: ColumnSizes) -> ColumnSizes:
    if not colsizes:
        return colsizes
    last_colsize = None
    for name, _, _ in BS_BREAKPOINTS:
        if name in colsizes:
            last_colsize = colsizes[name]
        elif last_colsize and name not in colsizes:
            colsizes[name] = last_colsize
    return colsizes


def get_imgsizes(colsizes):
    colsizes = fill_colsizes_upward(colsizes)
    sizes = []
    for name, screen_width, container_width in reversed(BS_BREAKPOINTS):
        col_size = colsizes.get(name)
        if col_size is None:
            # guess full width
            condition = "max-width" if container_width is None else "min-width"
            value = "100vw"
        else:
            col_ratio = "{:.2f}".format(col_size / COL_BASE)
            if container_width is None:
                condition = "max-width"
                value = "calc(100vw * {})".format(col_ratio)
            else:
                condition = "min-width"
                value = "calc(min({}px, 100vw) * {})".format(container_width, col_ratio)

        sizes.append(
            "({condition}: {screen_width}px) {value}".format(
                condition=condition,
                screen_width=screen_width,
                value=value,
            )
        )
    sizes.append("100vw")

    return ", ".join(sizes)


def get_responsive_image(
    thumbnails: List[ResponsiveImageThumbnail], column_sizes: ColumnSizes
) -> ResponsiveImage:
    by_alias = {thumbnail.alias: thumbnail for thumbnail in thumbnails}
    extra_source_types = get_extra_source_types()
    original_mime_type = ""
    all_source_types = [
        ResponsiveImageSourceTypes(mime_type=original_mime_type, extension=""),
    ] + extra_source_types
    srcset = get_srcsets(all_source_types, thumbnails)

    img_sizes = get_imgsizes(column_sizes)
    sources = [
        ResponsiveImageSource(
            srcset=srcset[source_type.mime_type],
            mime_type=source_type.mime_type,
        )
        for source_type in extra_source_types
    ]
    src = by_alias.get(settings.THUMBNAIL_DEFAULT_ALIAS)
    if src is None:
        src = by_alias.get("original")
    if src:
        src = src.url
    else:
        src = ""

    return ResponsiveImage(
        src=src,
        srcset=srcset[original_mime_type],
        sizes=img_sizes,
        sources=sources,
    )


def get_filer_thumbnails(
    filer_image, sizes=None, include_original=True, extra_opts=None
) -> List[ResponsiveImageThumbnail]:
    if sizes is None:
        sizes = [
            (alias, opt["size"])
            for alias, opt in settings.THUMBNAIL_ALIASES["filer.Image"].items()
        ]
    raise_errors = getattr(settings, "THUMBNAIL_DEBUG", False)
    thumbnails = []

    if extra_opts is None:
        extra_opts = {}

    if include_original:
        # generate thumbnail for original size
        # to trigger extra source types and optimiztions
        sizes.append(("original", (int(filer_image.width), int(filer_image.height))))

    thumbnailer = get_thumbnailer(filer_image)

    for alias, size in sizes:
        if size[0] > filer_image.width:
            continue
        try:
            thumbnail = thumbnailer.get_thumbnail(
                {
                    "size": size,
                    "subject_location": filer_image.subject_location,
                    **extra_opts,
                }
            )
        except Exception:
            if raise_errors:
                raise
            continue
        thumbnails.append(
            ResponsiveImageThumbnail(
                url=thumbnail.url, size=(thumbnail.width, thumbnail.height), alias=alias
            )
        )
    return thumbnails
