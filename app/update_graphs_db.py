import psycopg2
import datetime
import logging
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
import os
import re
from sqlalchemy.orm import Session

from dequa_graph.utils import load_graphs, add_waterbus_to_street
from utils.update_actv_data import get_updated_gtfs_files, get_last_actv_index, download_actv_data
from utils.logger import get_logger
from utils.io_db import get_engine_metadata, get_table, get_current_data, update_current_data_ids, insert_graph, find_highest_version_in_folder

# Load environment variables from .env
config = dotenv_values()

DB_CONFIG = {
    "engine": config.get("DB_ENGINE", "postgresql"),
    "dbname": config.get("DB_NAME", "dequa_data_versions"),
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

TBL_CURRENT_DATA = config.get("TBL_CURRENT_DATA", "current_data")
TBL_STREET = config.get("TBL_STREET", "graph_street")
TBL_WATER = config.get("TBL_WATER", "graph_water")
TBL_WATERBUS = config.get("TBL_WATERBUS", "graph_waterbus")

GRAPH_STREET_PATTERN = re.compile("dequa_ve_terra_v(\d+)_(\d{4})\.gt$")
GRAPH_WATER_PATTERN = re.compile("dequa_ve_acqua_v(\d+)_(\d{4}).*\.gt$")
GTFS_FILE_PATTERN = re.compile("actv_nav_(\d+)\.zip$")

FILE_FOLDER = Path(config.get("FILE_FOLDER", "files"))
GRAPHS_FOLDER = FILE_FOLDER / config.get("GRAPH_FOLDER","graphs")
GTFS_FOLDER = FILE_FOLDER / config.get("GTFS_FOLDER", "gtfs")

def main(logger):
    
    # Set database
    engine, meta_data = get_engine_metadata(DATABASE_URL)
    
    # Get tables
    tbl_curr_data = get_table(TBL_CURRENT_DATA, meta_data, engine)
    tbl_street = get_table(TBL_STREET, meta_data, engine)
    tbl_water = get_table(TBL_WATER, meta_data, engine)
    tbl_waterbus = get_table(TBL_WATERBUS, meta_data, engine)
    
    # conn = psycopg2.connect(**DB_CONFIG)
    
    # check folders to avoid problems
    if not any(f.exists for f in [GRAPHS_FOLDER, GTFS_FOLDER]):
        raise ValueError(f"File folders do not exist")
    
    with Session(engine) as session:
        curr_data = get_current_data(session, tbl_curr_data, tbl_water, tbl_street, tbl_waterbus)
        if curr_data:
            logger.info(f"Initial current versions: {curr_data}")

        # scan folder for last available version
        street_max_ver, street_max_path = find_highest_version_in_folder(GRAPHS_FOLDER, GRAPH_STREET_PATTERN)
        water_max_ver, water_max_path = find_highest_version_in_folder(GRAPHS_FOLDER, GRAPH_WATER_PATTERN)
        gtfs_max_num, gtfs_max_path = find_highest_version_in_folder(GTFS_FOLDER, GTFS_FILE_PATTERN)

        logger.info(f"File versions: street {street_max_ver}, water {water_max_ver}, gtfs {gtfs_max_num}")
        
        # check online gtfs file and eventually update
        last_gtfs_num, last_gtfs_data_name = get_last_actv_index()
        if last_gtfs_num > (gtfs_max_num or 0):
            logger.info(f"New ACTV file: {last_gtfs_data_name}")
            download_actv_data(last_gtfs_data_name, GTFS_FOLDER)
            gtfs_max_num, gtfs_max_path = find_highest_version_in_folder(GTFS_FOLDER, GTFS_FILE_PATTERN)


        # UPDATE GRAPH WATER
        new_water_uploaded = False
        if water_max_ver is not None and water_max_ver != (curr_data["graph_water_version"] or 0):
            logger.info(f"New local graph_water v{water_max_ver} found at {water_max_path}. Uploading.")
            wb_name = water_max_path.name
            wb_bytes = water_max_path.read_bytes()
            new_water_id = insert_graph(session, tbl_water, wb_name, wb_bytes, water_max_ver)
            new_current_data_id = update_current_data_ids(session, tbl_curr_data, curr_data["id"], water_id=new_water_id, updated_at=datetime.datetime.now())
            logger.info(f"Inserted graph_water id={new_water_id}, updated current_data.water_graph_id")
        
        # UPDATE STREET
        street_ver = curr_data["graph_street_version"] or 0
        gtfs_ver = curr_data["gtfs_number"] or 0
        
        need_rebuild = False
        
        if street_max_ver is not None and street_max_ver != street_ver:
            logger.info(f"New local graph_street v{street_max_ver} found at {street_max_path}. Will rebuild using this as street graph.")
            street_ver = street_max_ver
            need_rebuild = True

        if gtfs_max_num is not None and gtfs_max_num > gtfs_ver:
            logger.info(f"New local GTFS actv_nav_{gtfs_max_num}.zip found at {gtfs_max_path}. Will rebuild using new GTFS.")
            gtfs_ver = gtfs_max_num
            need_rebuild = True

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
            new_street_id = insert_graph(session, tbl_street, new_graph_street_only_name, street_data, street_max_ver)
            logger.info(f"Inserted graph_street id={new_street_id}")

            new_waterbus_id = insert_graph(session, tbl_waterbus, new_graph_street_plus_waterbus_name, waterbus_data, gtfs_ver, gtfs_valid_from, gtfs_valid_to, new_street_id)
            logger.info(f"Inserted graph_waterbus id={new_waterbus_id}")
            
            # Update current data in DB
            update_current_data_ids(session, tbl_curr_data, curr_data["id"], street_id=new_street_id, waterbus_id=new_waterbus_id, updated_at=datetime.datetime.now())
            logger.info("Database updated successfully")

        else:
            logger.info(f"No update.")
        session.commit()

        # conn.close()


if __name__ == '__main__':
    logger = get_logger(name="dequa_update", file="logs/automatic_tasks.log", level=logging.DEBUG)
    logger.info("#" * 50)
    logger.info("running the script")
    main(logger)