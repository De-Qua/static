"""
Download the POIs from OpenStreetMap and store them in the opendata database.

Usage:
    python update_poi_db.py                  # download + load
    python update_poi_db.py --download-only  # only download and save the snapshot
    python update_poi_db.py --from-file F    # load a saved snapshot, without downloading
    python update_poi_db.py --reset          # delete all the POIs before loading (same transaction)
"""
import argparse
import logging
import sys
from pathlib import Path

from dotenv import dotenv_values

from utils.logger import get_logger
from utils.osm_download import OverpassError, cleanup_snapshots, download_elements, load_snapshot, save_snapshot
from utils.osm_poi_db import PoiDatabase
from utils.osm_poi_mapping import DOWNLOAD_FILTERS, convert_elements

# Load environment variables from .env
config = dotenv_values()

DB_CONFIG = {
    "engine": config.get("DB_ENGINE", "postgresql"),
    "dbname": config.get("DB_NAME_OPENDATA", "opendata_ve_pg"),
    "user": config.get("DB_USER", "dequa"),
    "password": config.get("DB_PASSWORD", "dequa"),
    "host": config.get("DB_HOST", "localhost"),
    "port": int(config.get("DB_PORT", 5432)),
}

DB_SERVER = f"{DB_CONFIG['host']}"
if DB_CONFIG["user"]:
    DB_SERVER = f"{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_SERVER}"
if DB_CONFIG["port"]:
    DB_SERVER = f"{DB_SERVER}:{DB_CONFIG['port']}"

DATABASE_URL = f"{DB_CONFIG['engine']}://{DB_SERVER}/{DB_CONFIG['dbname']}"

FILE_FOLDER = Path(config.get("FILE_FOLDER", "files"))
POI_FOLDER = FILE_FOLDER / config.get("POI_FOLDER", "poi")
# Number of OSM snapshots kept in POI_FOLDER
SNAPSHOTS_TO_KEEP = 4


def parse_args():
    parser = argparse.ArgumentParser(description="Update the POIs from OpenStreetMap")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--download-only", action="store_true",
                        help="only download the POIs and save the snapshot, without loading them")
    source.add_argument("--from-file", type=Path,
                        help="load the POIs from a saved snapshot instead of downloading them")
    parser.add_argument("--reset", action="store_true",
                        help="delete all the POIs, categories and types before loading (single transaction)")
    return parser.parse_args()


def main(logger, args):
    # 1. Get the OSM elements: from a snapshot or from Overpass
    if args.from_file:
        elements, osm_timestamp = load_snapshot(args.from_file)
        logger.info(f"Loaded {len(elements)} elements from {args.from_file} (OSM data of {osm_timestamp})")
    else:
        try:
            elements, osm_timestamp = download_elements(DOWNLOAD_FILTERS)
        except OverpassError as e:
            # The download is complete or nothing: with partial data we would delete valid POIs
            logger.error(f"Download failed, database not updated: {e}")
            return 1
        save_snapshot(elements, osm_timestamp, POI_FOLDER)
        cleanup_snapshots(POI_FOLDER, keep=SNAPSHOTS_TO_KEEP)
        if args.download_only:
            return 0

    # 2. Convert them into POIs
    pois, skipped = convert_elements(elements)

    # 3. Store them in the database
    if args.reset:
        logger.warning("Reset: all the POIs, categories and types will be replaced")
    stats = PoiDatabase(DATABASE_URL).load(pois, reset=args.reset)

    logger.info("-" * 50)
    logger.info(f"OSM data of {osm_timestamp}: {len(elements)} elements, {len(pois)} POIs")
    logger.info(f"Skipped elements: {dict(skipped)}")
    logger.info(f"Database: {dict(stats)}")
    if stats["error"]:
        logger.warning(f"{stats['error']} POIs could not be stored, see the errors above")
    return 0


if __name__ == "__main__":
    args = parse_args()
    logger = get_logger(name="dequa_update_poi", level=logging.DEBUG)
    logger.info("#" * 50)
    logger.info("Updating the POIs from OpenStreetMap")
    sys.exit(main(logger, args))
