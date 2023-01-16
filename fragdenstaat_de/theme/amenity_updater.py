import os
import subprocess
import tempfile
from datetime import datetime

from django.conf import settings

import requests
from django_amenities.updater import AmenityUpdater


def get_osmosis_arguments(input_filename, output_filename):
    yield "osmosis"
    count_inputs = 0
    value_tags = []
    wildcard_tags = []
    for _project, tag_list in settings.AMENITY_TOPICS.items():
        for key, value in tag_list:
            if value == "*":
                wildcard_tags.append(key)
            else:
                value_tags.append(f"{key}.{value}")

    if value_tags:
        joined_tags = ",".join(value_tags)
        count_inputs += 1
        yield from [
            "--read-pbf",
            input_filename,
            "--log-progress",
            "--node-key-value",
            f'keyValueList="{joined_tags!r}"',
            "--sort",
        ]

    for tag in wildcard_tags:
        count_inputs += 1
        yield from [
            "--read-pbf",
            input_filename,
            "--log-progress",
            "--tf",
            "accept-nodes",
            f"{tag}=*",
            "--sort",
        ]
    for _ in range(count_inputs - 1):
        yield "--merge"
    yield from ["--write-xml", output_filename]


LAST_UPDATE_FILENAME = "amenity_last_update.txt"


def find_last_update_time():
    try:
        with open(LAST_UPDATE_FILENAME) as f:
            return datetime.strptime(f.read(), "%Y-%m-%d")
    except Exception:
        return None


def write_last_update(date):
    with open(LAST_UPDATE_FILENAME, "w") as f:
        f.write(date.strftime("%Y-%m-%d"))


def update_osm_amenities():
    timestamp = find_last_update_time()
    LATEST_OSM_URL = "https://download.geofabrik.de/europe/germany-latest.osm.pbf"
    filename = LATEST_OSM_URL.split("/")[-1]
    next_filename = "germany_nodes.pbf"
    output_filename = "amenities.xml"

    with tempfile.TemporaryDirectory() as tmpdirname:
        filepath = os.path.join(tmpdirname, filename)
        # Download latest germany OSM file
        download_file_to_temp_dir(LATEST_OSM_URL, filepath)

        # Convert to nodes only
        run_command(
            [
                "osmconvert",
                filename,
                "--all-to-nodes",
                f"-o={next_filename}",
                "--max-objects=1000000000",
            ],
            tmpdirname,
            timeout=60.0 * 10,
        )
        # Filter and convert to XML
        arguments = list(get_osmosis_arguments(next_filename, output_filename))
        run_command(arguments, tmpdirname, timeout=60.0 * 10)

        # Update amenities in database
        updater = AmenityUpdater(
            os.path.join(tmpdirname, output_filename),
            timestamp=timestamp,
            topics=settings.AMENITY_TOPICS,
            delete_obsolete=False,
            category_func=getattr(settings, "AMENITY_CATEGORY_FUNC", None),
        )
        updater.run()
    write_last_update(datetime.now())


def run_command(arguments, working_dir, timeout=None):
    _out, err = "", ""
    p = None
    try:
        p = subprocess.Popen(
            arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=working_dir
        )

        _out, err = p.communicate(timeout=timeout)
        return
    except subprocess.TimeoutExpired:
        if p is not None:
            p.kill()
            _out, err = p.communicate()
    finally:
        if p is not None and p.returncode is None:
            p.kill()
            _out, err = p.communicate()
    raise Exception(err)


def download_file_to_temp_dir(url, filepath):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
