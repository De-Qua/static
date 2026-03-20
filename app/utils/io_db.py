from pathlib import Path
import re
import sqlalchemy as db
from sqlalchemy.orm import Session

import datetime
import psycopg2

def get_engine_metadata(DATABASE_URL):
    engine = db.create_engine(DATABASE_URL)
    meta_data = db.MetaData(bind=engine)
    meta_data.reflect()
    return engine, meta_data

def get_table(tbl_name, meta_data, engine):
    tbl = db.Table(tbl_name, meta_data, autoload_with=engine)
    return tbl

def insert_tide(tide, DATABASE_URL):
    engine, meta_data = get_engine_metadata(DATABASE_URL)
    tbl_tide = get_table('tide_new', meta_data, engine)
    tbl_curr_data = get_table('current_data', meta_data, engine)
    
    with Session(engine) as session:
        pass


def get_current_data(session, tbl_curr_data, tbl_water, tbl_street, tbl_waterbus):
    """Retrieve current data info from the DB instead of YAML."""
    query = (
        db.select(
            tbl_curr_data.c.id,
            tbl_waterbus.c.gtfs_number,
            tbl_street.c.version.label("graph_street_version"),
            tbl_water.c.version.label("graph_water_version"),
        )
        .outerjoin(tbl_street, tbl_street.c.id == tbl_curr_data.c.street_graph_id)
        .outerjoin(tbl_water, tbl_water.c.id == tbl_curr_data.c.water_graph_id)
        .outerjoin(tbl_waterbus, tbl_waterbus.c.id == tbl_curr_data.c.waterbus_graph_id)
    )
    curr_data = session.execute(query).first()
    
    if not curr_data:
        # create a first empty entry
        session.execute(tbl_curr_data.insert())
        curr_data = session.execute(query).first()
    
    return curr_data
    


def update_current_data_ids(session, tbl_curr_data, curr_data_id, street_id=None, water_id=None, waterbus_id=None, updated_at=None, gtfs_number=None):
    """
    Insert or update the current_data row.

    If current_id == 0 or None, inserts a new row and returns the new id.
    Otherwise, updates the existing row and returns the same id.
    """
    
    updated_curr_data = {}
    if street_id:
        updated_curr_data["street_graph_id"] = street_id
    if water_id:
        updated_curr_data["water_graph_id"] = water_id
    if waterbus_id:
        updated_curr_data["waterbus_graph_id"] = waterbus_id
    if updated_at:
        updated_curr_data["graph_updated_at"] = updated_at
        
    if curr_data_id:
        updated_curr_data["id"] = curr_data_id
        session.query(tbl_curr_data).update(updated_curr_data)
    else:
        res = session.execute(tbl_curr_data.insert(updated_curr_data))
        updated_curr_data["id"] = res.inserted_primary_key[0]
    
    return updated_curr_data["id"]


def insert_graph(session, tbl, name, data, version, valid_from=None, valid_to=None, street_id=None):
    """Insert new graph_street and graph_waterbus rows and return their IDs."""
    
    new_data = {
        "name": name,
        "data": data,
        "created_at": datetime.datetime.now(),
    }
    
    if "version" in tbl.columns.keys():
        new_data["version"] = version

    if "gtfs_number" in tbl.columns.keys():
        new_data["gtfs_number"] = version
        new_data["valid_from"] = valid_from
        new_data["valid_to"] = valid_to
        new_data["graph_street_id"] = street_id
    
    res = session.execute(tbl.insert(new_data))
    res_id = res.inserted_primary_key[0]
    return res_id


def find_highest_version_in_folder(folder: Path, pattern: re.Pattern):
    """
    Return tuple (max_version:int or None, path_to_max:Path or None).
    Scans folder for files matching pattern and extracts version group(1).
    """
    max_ver = None
    max_path = None
    if not folder.exists():
        return None, None
    for p in folder.iterdir():
        if not p.is_file():
            continue
        m = pattern.search(p.name)
        if not m:
            continue
        try:
            v = int(m.group(1))
        except Exception:
            continue
        if (max_ver is None) or (v > max_ver) or (v == max_ver and p.stat().st_mtime > max_path.stat().st_mtime):
            max_ver = v
            max_path = p
    return max_ver, max_path