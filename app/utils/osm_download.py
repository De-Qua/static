"""
Download POIs from OpenStreetMap through the Overpass API and store them as JSON snapshots.
"""
import datetime
import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger("dequa_update_poi.osm_download")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Overpass area id of a relation = 3600000000 + relation id (44741 = Comune di Venezia)
VENICE_AREA_OFFSET = 3600000000
AREA_RELATIONS = {
    6628638: "Venezia-Murano-Burano",
    6628635: "Lido-Pellestrina",
    3049430: "Laguna di Venezia",
}
AREA_IDS = [VENICE_AREA_OFFSET + relation_id for relation_id in AREA_RELATIONS]

USER_AGENT = "DeQua POI updater (https://dequa.it)"

QUERY_TIMEOUT_S = 180       # server-side timeout of each Overpass query
SLEEP_BETWEEN_QUERIES_S = 5
RETRY_WAITS_S = [30, 60, 120]  # waits before each retry
RETRY_STATUS_CODES = {429, 502, 503, 504}

SNAPSHOT_PREFIX = "osm_poi_"


class OverpassError(Exception):
    """Raised when a query keeps failing after all the retries."""


def build_query(tag, extra_filter="", area_ids=AREA_IDS):
    """Overpass QL query for all nodes, ways and relations with the given tag inside the area."""
    areas = "".join(f"area(id:{area_id});" for area_id in area_ids)
    return f"""
    [out:json][timeout:{QUERY_TIMEOUT_S}];
    ({areas})->.a;
    nwr["{tag}"]{extra_filter}(area.a);
    out center;
    """


def run_query(query, url=OVERPASS_URL):
    """Run an Overpass query, retrying on temporary errors. Returns the decoded JSON."""
    attempts = len(RETRY_WAITS_S) + 1
    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(url, data={"data": query},
                                     headers={"User-Agent": USER_AGENT},
                                     timeout=QUERY_TIMEOUT_S + 30)
            if response.status_code == 200:
                return response.json()
            if response.status_code not in RETRY_STATUS_CODES:
                raise OverpassError(f"Overpass returned {response.status_code}: {response.text[:200]}")
            reason = f"status {response.status_code}"
        except (requests.Timeout, requests.ConnectionError) as e:
            reason = type(e).__name__

        if attempt == attempts:
            raise OverpassError(f"Overpass query failed after {attempts} attempts ({reason})")
        wait = RETRY_WAITS_S[attempt - 1]
        logger.warning(f"Overpass query failed ({reason}), retrying in {wait}s ({attempt}/{attempts - 1})")
        time.sleep(wait)


def download_elements(tags, area_ids=AREA_IDS):
    """
    Download all the OSM elements having at least one of the tags inside the area.
    Returns (elements, osm_timestamp): elements are deduplicated by (type, id).
    Raises OverpassError if a tag cannot be downloaded.
    """
    elements = {}
    osm_timestamp = None
    for i, (tag, extra_filter) in enumerate(tags):
        if i > 0:
            time.sleep(SLEEP_BETWEEN_QUERIES_S)
        data = run_query(build_query(tag, extra_filter, area_ids))
        tag_elements = data.get("elements", [])
        osm_timestamp = data.get("osm3s", {}).get("timestamp_osm_base", osm_timestamp)
        new = 0
        for element in tag_elements:
            key = (element["type"], element["id"])
            if key not in elements:
                elements[key] = element
                new += 1
        logger.info(f"Tag '{tag}{extra_filter}': {len(tag_elements)} elements ({new} new)")

    logger.info(f"Downloaded {len(elements)} unique elements for {len(tags)} tags")
    return list(elements.values()), osm_timestamp


def save_snapshot(elements, osm_timestamp, folder):
    """Save the elements in a dated JSON file and return its path."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now()
    path = folder / f"{SNAPSHOT_PREFIX}{now.strftime('%Y-%m-%d_%H%M')}.json"
    snapshot = {
        "downloaded_at": now.isoformat(timespec="seconds"),
        "osm_timestamp": osm_timestamp,
        "elements": elements,
    }
    with open(path, "w") as f:
        json.dump(snapshot, f)
    logger.info(f"Saved {len(elements)} elements in {path}")
    return path


def load_snapshot(path):
    """Load a snapshot saved by save_snapshot. Returns (elements, osm_timestamp)."""
    with open(path) as f:
        snapshot = json.load(f)
    return snapshot["elements"], snapshot.get("osm_timestamp")


def cleanup_snapshots(folder, keep=4):
    """Delete the oldest snapshots, keeping the most recent `keep` ones."""
    snapshots = sorted(Path(folder).glob(f"{SNAPSHOT_PREFIX}*.json"))
    for path in snapshots[:-keep] if keep > 0 else snapshots:
        path.unlink()
        logger.info(f"Deleted old snapshot {path}")
