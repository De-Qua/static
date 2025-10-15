import psycopg2
import datetime
import logging
from pathlib import Path
from dotenv import load_dotenv
import os
import re

from dequa_graph.utils import load_graphs, add_waterbus_to_street
from utils.update_actv_data import get_updated_gtfs_files, get_last_actv_index, download_actv_data
from utils.logger import get_logger
from utils.io_db import get_current_data, update_current_data_ids, insert_graph, find_highest_version_in_folder

# Load environment variables from .env
load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "dequa_data_versions"),
    "user": os.getenv("POSTGRES_USER", "dequa"),
    "password": os.getenv("POSTGRES_PASSWORD", "dequa"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
}

GRAPH_STREET_PATTERN = re.compile("dequa_ve_terra_v(\d+)_(\d{4})\.gt$")
GRAPH_WATER_PATTERN = re.compile("dequa_ve_acqua_v(\d+)_(\d{4}).*\.gt$")
GTFS_FILE_PATTERN = re.compile("actv_nav_(\d+)\.zip$")

FILE_FOLDER = Path(os.getenv("FILE_FOLDER", "files"))
GRAPHS_FOLDER = FILE_FOLDER / os.getenv("GRAPH_FOLDER","graphs")
GTFS_FOLDER = FILE_FOLDER / os.getenv("GTFS_FOLDER", "gtfs")

def main(logger):
    conn = psycopg2.connect(**DB_CONFIG)

    current = get_current_data(conn)

    # create folders to avoid problems
    for f in [GRAPHS_FOLDER, GTFS_FOLDER]:
        f.mkdir(parents=True, exist_ok=True)

    # scan folder for last available version
    street_max_ver, street_max_path = find_highest_version_in_folder(GRAPHS_FOLDER, GRAPH_STREET_PATTERN)
    water_max_ver, water_max_path = find_highest_version_in_folder(GRAPHS_FOLDER, GRAPH_WATER_PATTERN)
    gtfs_max_num, gtfs_max_path = find_highest_version_in_folder(GTFS_FOLDER, GTFS_FILE_PATTERN)

    # check online gtfs file and eventually update
    last_gtfs_num, last_gtfs_data_name = get_last_actv_index()
    if last_gtfs_num > gtfs_max_num:
        logger.info(f"New ACTV file: {last_gtfs_data_name}")
        download_actv_data(last_gtfs_data_name, GTFS_FOLDER)
        gtfs_max_num, gtfs_max_path = find_highest_version_in_folder(GTFS_FOLDER, GTFS_FILE_PATTERN)


    # UPDATE GRAPH WATER
    new_water_uploaded = False
    if water_max_ver is not None and water_max_ver > (current["graph_water_version"] or 0):
        logger.info(f"New local graph_water v{water_max_ver} found at {water_max_path}. Uploading.")
        wb_name = water_max_path.name
        wb_bytes = water_max_path.read_bytes()
        new_water_id = insert_graph(conn, 'water', wb_name, wb_bytes, water_max_ver)
        update_current_data_ids(conn, current["id"], water_id=new_water_id, updated_at=datetime.datetime.now())
        logger.info(f"Inserted graph_water id={new_water_id}, updated current_data.water_graph_id")
        # Update local in-memory current state
        current["graph_water_version"] = water_max_ver
        current["water_graph_id"] = new_water_id
        new_water_uploaded = True
    
    # UPDATE STREET
    street_ver = current["graph_street_version"] or 0
    gtfs_ver = current["gtfs_number"]
    
    need_rebuild = False
    
    if street_max_ver is not None and street_max_ver != street_ver:
        logger.info(f"New local graph_street v{street_max_ver} found at {street_max_path}. Will rebuild using this as street graph.")
        street_ver = street_max_ver
        need_rebuild = True

    if gtfs_max_num is not None and gtfs_max_num > gtfs_ver:
        logger.info(f"New local GTFS actv_nav_{gtfs_max_num}.zip found at {gtfs_max_path}. Will rebuild using new GTFS.")
        gtfs_ver = gtfs_max_num
        need_rebuild = True

    import pdb
    pdb.set_trace()
    graph_street_path = GRAPHS_FOLDER / street_max_path.name
    
    if need_rebuild:
        
        start_date = datetime.date.today()
        path_zip_files_actv, gtfs_valid_from, gtfs_valid_to = get_updated_gtfs_files(logger, file_folder=GTFS_FOLDER, start_date=start_date)

        logger.debug("Loading graphs...")
        graph_street = load_graphs(str(graph_street_path))
        graph_street_only, graph_street_plus_waterbus = add_waterbus_to_street(graph_street, path_zip_files_actv)

        today_time = datetime.datetime.today().strftime("%Y-%m-%d")
        
        new_graph_street_only_name = f"graph_street_only_file_{today_time}.gt"
        new_graph_street_only_path = GRAPHS_FOLDER / new_graph_street_only_name
        graph_street_only.save(str(new_graph_street_only_path))

        new_graph_street_plus_waterbus_name = f"graph_street_plus_waterbus_file_{today_time}.gt"
        new_graph_street_plus_waterbus_path = GRAPHS_FOLDER / new_graph_street_plus_waterbus_name
        graph_street_plus_waterbus.save(str(new_graph_street_plus_waterbus_path))

        # Read files as bytes
        street_data = new_graph_street_only_path.read_bytes()
        waterbus_data = new_graph_street_plus_waterbus_path.read_bytes()

        # Insert graphs in DB
        new_street_id = insert_graph(conn, 'street', new_graph_street_only_name, street_data, street_max_ver)
        new_waterbus_id = insert_graph(conn, 'waterbus', new_graph_street_plus_waterbus_name, waterbus_data, gtfs_ver, gtfs_valid_from, gtfs_valid_to, new_street_id)

        # Update current data in DB
        update_current_data_ids(conn, current["id"], street_id=new_street_id, waterbus_id=new_waterbus_id, updated_at=datetime.datetime.now())
        logger.info("Database updated successfully")

    else:
        logger.info("No update")

    conn.close()


if __name__ == '__main__':
    logger = get_logger(name="dequa_update", file="logs/automatic_tasks.log", level=logging.DEBUG)
    logger.info("#" * 50)
    logger.info("running the script")
    main(logger)