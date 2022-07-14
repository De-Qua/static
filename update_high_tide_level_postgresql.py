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

DATABASE_URL = "postgresql:///opendata_ve_pg"

URL_TIDE = 'https://dati.venezia.it/sites/default/files/dataset/opendata/livello.json'
DT_TIDE_FORMAT = "%Y-%m-%d %H:%M:%S %z"
MAX_NUM_ROWS = 1 * 24 * 12  # num_days * 24 [hours in a day] * 12 [tide data in one hour]
# Set the logger
logger = logging.getLogger('high tide')
logger.setLevel(logging.DEBUG)


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
        "latDMSN": float(data["latDMSN"]),
        "lonDMSE": float(data["lonDMSE"]),
        "latDDN": float(data["latDDN"]),
        "lonDDE": float(data["lonDDE"]),
        # then we upload the time as basic utc
        "updated_at": dt_with_tzinfo.astimezone(pytz.utc).replace(tzinfo=None),
        "value": float(data["valore"][:-1])
    }


def main():
    tide = get_tide_data()
    if not tide:
        return
    tide["uploaded_at"] = dt.datetime.utcnow().replace(tzinfo=None)
    # Set database
    engine = db.create_engine(DATABASE_URL)
    meta_data = db.MetaData(bind=engine)
    db.MetaData.reflect(meta_data)

    # get the table "tide"
    tbl_tide = db.Table('tide', meta_data, autoload=True)
    # insert in the table
    new_tide = tbl_tide.insert(tide)

    # commit the changes to the db
    with Session(engine) as session:
        num_rows = session.query(tbl_tide).count()
        last_row = session.query(tbl_tide).order_by(tbl_tide.c.id.desc()).first()
        if last_row.updated_at == tide["updated_at"]:
            print("already in db")
        else:
            if num_rows >= 100:
                to_be_deleted = tbl_tide.delete().where(tbl_tide.c.id < last_row.id - MAX_NUM_ROWS)
                session.execute(to_be_deleted)
            session.execute(new_tide)
            session.commit()


if __name__ == "__main__":
    main()
