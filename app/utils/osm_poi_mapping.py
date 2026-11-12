"""
Convert OSM elements (as returned by Overpass) into POI data ready to be stored in the database.
No database access here: only mapping tables and pure functions.
"""
import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("dequa_update_poi.poi_mapping")

# Overpass filters to download: (OSM key, extra Overpass filter).
# Keys with many elements that are not POIs (buildings, trees, canals, ...) are downloaded only if named.
# Not downloaded: highway (streets, already in the street table), boundary, route.
DOWNLOAD_FILTERS = [
    ("amenity", ""),
    ("shop", ""),
    ("tourism", ""),
    ("craft", ""),
    ("office", ""),
    ("healthcare", ""),
    ("emergency", ""),
    ("historic", ""),
    ("leisure", ""),
    ("public_transport", ""),
    ("railway", ""),
    ("power", ""),
    ("building", '["name"]'),
    ("natural", '["name"]'),
    ("landuse", '["name"]'),
    ("place", '["name"]'),
    ("water", '["name"]'),
    ("waterway", '["name"]'),
    ("highway", '["highway"="bus_stop"]'),
]

# OSM keys that become a POI category; the tag value becomes the type (e.g. amenity=restaurant).
# cuisine and sport are not downloaded on their own but add types to the downloaded POIs.
CATEGORY_KEYS = [key for key, _ in DOWNLOAD_FILTERS] + ["cuisine", "sport"]

# Tag values that do not describe a type
IGNORED_VALUES = {"no"}

# Values meaning "it is a <key>" without saying which type (e.g. building=yes): not a useful type
GENERIC_VALUES = {"yes"}

# OSM tag -> poi column. If two tags map to the same column, the first one found wins.
COLUMN_TAGS = {
    "name": "name",
    "opening_hours": "opening_hours",
    "wheelchair": "wheelchair",
    "toilets": "toilets",
    "toilets:wheelchair": "toilets_wheelchair",
    "wikipedia": "wikipedia",
    "atm": "atm",
    "phone": "phone",
    "contact:phone": "phone",
}
BOOLEAN_COLUMNS = {"toilets", "toilets_wheelchair", "atm"}
BOOLEAN_VALUES = {"yes": True, "no": False}

# OSM tag -> kind of alternative name (stored in poi_name). name:<lang> tags have kind 'lang'.
ALT_NAME_TAGS = {
    "alt_name": "alt",
    "old_name": "old",
    "short_name": "short",
    "loc_name": "loc",
    "official_name": "official",
}
# name:<lang> with a language code such as it, en, vec, zh-Hans (excludes e.g. name:etymology:wikidata)
LANG_NAME_TAG = re.compile(r"^name:([a-z]{2,3}(?:-[A-Za-z]+)?)$")

# POIs that do not belong to a house number (fountains, benches, ...): they get their own location
STANDALONE_TYPES = {
    "amenity": {"drinking_water", "bench", "toilets", "clock", "waste_basket", "recycling",
                "ferry_terminal", "place_of_worship", "bus_station"},
    "shop": {"newsagent", "kiosk"},
    "building": {"kiosk", "tower", "ruins", "church", "column"},
    "man_made": {"water_well", "tower"},
    "historic": {"memorial", "archaeological_site", "building"},
    "memorial": {"statue"},
    "public_transport": {"platform", "station"},
    "leisure": {"marina", "pitch", "park", "swimming_pool", "garden"},
    "water": {"canal", "harbour"},
    "tourism": {"viewpoint", "attraction", "information", "artwork"},
    "landuse": {"cemetery"},
}

# Relations that are not POIs
SKIPPED_RELATION_TYPES = {"route", "boundary"}


@dataclass
class OsmPoi:
    osm_type: str
    osm_id: int
    lat: float
    lon: float
    columns: Dict[str, object]                     # poi column -> value (not truncated)
    categories: List[Tuple[str, str]]              # (category, type)
    names: List[Tuple[str, str, Optional[str]]]    # alternative names: (name, kind, lang)
    osm_tags: Dict[str, str]                       # all the original OSM tags
    standalone_location: bool


def split_values(value):
    """OSM multiple values are separated by ';'"""
    return [v.strip() for v in value.split(";") if v.strip()]


def get_coordinates(element):
    """Nodes have lat/lon, ways and relations have a center (from 'out center')."""
    if element["type"] == "node":
        return element.get("lat"), element.get("lon")
    center = element.get("center") or {}
    return center.get("lat"), center.get("lon")


def get_categories(tags):
    categories = []
    generic_keys = []
    for key in CATEGORY_KEYS:
        if key not in tags:
            continue
        for value in split_values(tags[key]):
            value_lower = value.lower()
            if value_lower in IGNORED_VALUES:
                continue
            if value_lower in GENERIC_VALUES:
                generic_keys.append(key)
                continue
            if (key, value) not in categories:
                categories.append((key, value))
    if not categories:
        categories.append((key, key) for key in generic_keys)
    return categories


def get_columns(tags):
    columns = {}
    for tag, column in COLUMN_TAGS.items():
        if tag not in tags or column in columns:
            continue
        value = tags[tag]
        if column in BOOLEAN_COLUMNS:
            value = BOOLEAN_VALUES.get(value.strip().lower())
        elif column == "phone":
            # sometimes there are several numbers: keep the first one
            phones = split_values(value)
            value = phones[0] if phones else None
        columns[column] = value
    return columns


def get_alternative_names(tags):
    main_name = tags.get("name")
    names = []
    for tag, value in tags.items():
        if tag in ALT_NAME_TAGS:
            kind, lang = ALT_NAME_TAGS[tag], None
        else:
            match = LANG_NAME_TAG.match(tag)
            if not match:
                continue
            kind, lang = "lang", match.group(1)
        for name in split_values(value):
            # a translation equal to the main name adds nothing
            if kind == "lang" and name == main_name:
                continue
            if (name, kind, lang) not in names:
                names.append((name, kind, lang))
    return names


def is_standalone(tags):
    return any(value in STANDALONE_TYPES[key]
               for key in STANDALONE_TYPES if key in tags
               for value in split_values(tags[key]))


def skip_reason(element):
    """Why an element must not become a POI, or None if it is a valid POI."""
    tags = element.get("tags") or {}
    if not tags:
        return "no_tags"
    if element["type"] == "relation" and tags.get("type") in SKIPPED_RELATION_TYPES:
        return f"relation_{tags['type']}"
    lat, lon = get_coordinates(element)
    if lat is None or lon is None:
        return "no_coordinates"
    if not get_categories(tags):
        return "no_category"
    return None


def osm_to_poi(element):
    """Convert a valid OSM element (skip_reason is None) into an OsmPoi."""
    tags = element["tags"]
    lat, lon = get_coordinates(element)
    return OsmPoi(
        osm_type=element["type"],
        osm_id=element["id"],
        lat=lat,
        lon=lon,
        columns=get_columns(tags),
        categories=get_categories(tags),
        names=get_alternative_names(tags),
        osm_tags=dict(tags),
        standalone_location=is_standalone(tags),
    )


def convert_elements(elements):
    """Convert all the elements. Returns (pois, skipped) where skipped counts the skip reasons."""
    pois = []
    skipped = Counter()
    for element in elements:
        reason = skip_reason(element)
        if reason:
            skipped[reason] += 1
        else:
            pois.append(osm_to_poi(element))
    logger.info(f"Converted {len(pois)} POIs out of {len(elements)} elements, skipped: {dict(skipped)}")
    return pois, skipped
