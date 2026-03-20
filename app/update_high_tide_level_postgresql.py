import requests
import os
import json
import sys
import time
import datetime as dt
import logging
import sqlalchemy as db
from sqlalchemy.orm import Session
import pytz
from dotenv import load_dotenv
from utils.logger import get_logger


# Load environment variables from .env
config = load_dotenv()

DB_CONFIG = {
    "engine": config.get("ENGINE", "postgresql"),
    "dbname": config.get("POSTGRES_DB", "dequa_data_versions"),
    "user": config.get("POSTGRES_USER", "dequa"),
    "password": config.get("POSTGRES_PASSWORD", "dequa"),
    "host": config.get("POSTGRES_HOST", "localhost"),
    "port": int(config.get("POSTGRES_PORT", 5432)),
}

DB_SERVER = f"{DB_CONFIG['host']}"
if DB_CONFIG["user"]:
    DB_SERVER = f"{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_SERVER}"
if DB_CONFIG["port"]:
    DB_SERVER = f"{DB_SERVER}:{DB_CONFIG['port']}"

DATABASE_URL = f"{DB_CONFIG['engine']}://{DB_SERVER}/{DB_CONFIG['dbname']}"

URL_TIDE = 'https://dati.venezia.it/sites/default/files/dataset/opendata/livello.json'
DT_TIDE_FORMAT = "%Y-%m-%d %H:%M:%S %z"
MAX_NUM_ROWS = 1 * 24 * 12  # num_days * 24 [hours in a day] * 12 [tide data in one hour]
MAX_ATTEMPTS = 3
INTER_ATTEMPT_TIME = 30 # seconds



def get_tide_data():
    # get the data from the tide
    resp = requests.get(url=URL_TIDE)
    if resp.status_code != 200:
        logger.warning(f"Url tide does not reply correctly: status {resp.status_code}")
        return {}
    data = resp.json()
    selected_data = extract_data_from_array(data)
    if not selected_data:
        return {}
    return format_tide_data(selected_data)


def extract_data_from_array(array_tides):
    for short_name in ["PSalute", "PS_Giud"]:
        data = [d for d in array_tides if d["nome_abbr"] == short_name]
        if data:
            return data[0]
    return []


def format_tide_data(data):
    # we manually add the utc+1 that is the time how the data are stored
    data_with_tzinfo = data["data"] + " +0100"
    dt_with_tzinfo = dt.datetime.strptime(data_with_tzinfo, DT_TIDE_FORMAT)
    return {
        "id_station": data["ID_stazione"],
        "station": data["stazione"],
        "short_name": data["nome_abbr"],
        "latDMSN": float(data.get("latDMSN", 0)),
        "lonDMSE": float(data.get("lonDMSE", 0)),
        "latDDN": float(data.get("latDDN", 0)),
        "lonDDE": float(data.get("lonDDE", 0)),
        # then we upload the time as basic utc
        "updated_at": dt_with_tzinfo.astimezone(pytz.utc).replace(tzinfo=None),
        "value": float(data["valore"][:-1])
    }


def main(logger):
    counter_attempts = 0
    finished = False
    while counter_attempts < MAX_ATTEMPTS and not finished:
        # update the counter and sleep (except in the first case)
        if counter_attempts > 0:
            time.sleep(INTER_ATTEMPT_TIME)
        counter_attempts += 1

        tide = get_tide_data()
        if tide:
            finished = True

    if finished:
        tide["uploaded_at"] = dt.datetime.utcnow().replace(tzinfo=None)
        # Set database
        engine = db.create_engine(DATABASE_URL)
        meta_data = db.MetaData(bind=engine)
        meta_data.reflect()

        # get the table "tide" and "current data"
        tbl_tide = db.Table('tide_new', meta_data, autoload_with=engine)
        tbl_curr_data = db.Table('current_data', meta_data, autoload_with=engine)
            
        # insert in the table
        new_tide = tbl_tide.insert(tide)

        # commit the changes to the db
        with Session(engine) as session:
            num_rows = session.query(tbl_tide).count()
            last_row = session.query(tbl_tide).order_by(tbl_tide.c.id.desc()).first()
            if num_rows > 0 and last_row.updated_at == tide["updated_at"]:
                logger.info("Tide is already up to date")
            else:
                if num_rows >= 100:
                    to_be_deleted = tbl_tide.delete().where(tbl_tide.c.id < last_row.id - MAX_NUM_ROWS)
                    session.execute(to_be_deleted)
                res_tide = session.execute(new_tide)
                res_tide_id = res_tide.inserted_primary_key[0]
                
                # Update current data table
                curr_data = session.query(tbl_curr_data).first()
                new_curr_data = {
                    'tide_id': res_tide_id
                }
                if curr_data:
                    new_curr_data['id'] = curr_data['id']
                    session.query(tbl_curr_data).update(new_curr_data)
                else:
                    session.execute(tbl_curr_data.insert(new_curr_data))

                # Commit everythin
                session.commit()
                logger.info("Tide updated")
    else:
        logger.warning("I was not able to download the tide")

if __name__ == "__main__":
    logger = get_logger(name="high_tide", file="logs/automatic_tasks_high_tide.log", level=logging.DEBUG)
    # Set the logger
    logger.info("#" * 50)
    logger.info("running the script")
    main(logger)
