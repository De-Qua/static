from pathlib import Path
import re

import datetime
import psycopg2

def get_current_data(conn):
    """Retrieve current data info from the DB instead of YAML."""
    current_data = {
        "id": 0,
        "gtfs_number": 0,
        "graph_street_version": 0,
        "graph_water_version": 0,
    }
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.id,
                   gws.gtfs_number,
                   gs.version AS graph_street_version,
                   gw.version AS graph_water_version
            FROM current_data c
            JOIN graph_street gs ON gs.id = c.street_graph_id
            JOIN graph_water gw ON gw.id = c.water_graph_id
            JOIN graph_waterbus gws ON gws.id = c.waterbus_graph_id
            LIMIT 1;
        """)
        row = cur.fetchone()
        if not row:
            print("No CurrentData found in database")
        else:
            current_data["id"] = row[0]
            current_data["gtfs_number"] = row[1]
            current_data["graph_street_version"] = row[2]
            current_data["graph_water_version"] = row[3]
        return current_data


def update_current_data_ids(conn, current_id, street_id=None, water_id=None, waterbus_id=None, updated_at=None, gtfs_number=None):
    """
    Insert or update the current_data row.

    If current_id == 0 or None, inserts a new row and returns the new id.
    Otherwise, updates the existing row and returns the same id.
    """
    fields = []
    values = []
    if street_id is not None:
        fields.append("street_graph_id")
        values.append(street_id)
    if water_id is not None:
        fields.append("water_graph_id")
        values.append(water_id)
    if waterbus_id is not None:
        fields.append("waterbus_graph_id")
        values.append(waterbus_id)
    if updated_at is not None:
        fields.append("graph_updated_at")
        values.append(updated_at)
    if gtfs_number is not None:
        fields.append("gtfs_last_number")
        values.append(gtfs_number)

    if not fields:
        return current_id

    with conn.cursor() as cur:
        if not current_id or current_id == 0:
            # INSERT new row
            columns_sql = ", ".join(fields)
            placeholders = ", ".join(["%s"] * len(values))
            query = f"INSERT INTO current_data ({columns_sql}) VALUES ({placeholders}) RETURNING id;"
            cur.execute(query, values)
            new_id = cur.fetchone()[0]
            conn.commit()
            return new_id
        else:
            # UPDATE existing row
            set_clause = ", ".join([f"{col} = %s" for col in fields])
            values.append(current_id)
            query = f"UPDATE current_data SET {set_clause} WHERE id = %s;"
            cur.execute(query, values)
            conn.commit()
            return current_id


def insert_graph(conn, graph_type, name, data, version, valid_from=None, valid_to=None, street_id=None):
    """Insert new graph_street and graph_waterbus rows and return their IDs."""
    with conn.cursor() as cur:
        if graph_type == "street":
            # Insert street graph
            cur.execute("""
                INSERT INTO graph_street (name, version, created_at, data)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (name, version, datetime.datetime.now(), psycopg2.Binary(data)))
        elif graph_type == "water":
            # Insert street graph
            cur.execute("""
                INSERT INTO graph_water (name, version, created_at, data)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (name, version, datetime.datetime.now(), psycopg2.Binary(data)))
        elif graph_type == "waterbus":
            # Insert waterbus graph
            cur.execute("""
                INSERT INTO graph_waterbus (name, created_at, data, gtfs_number, valid_from, valid_to, graph_street_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (
                name,
                datetime.datetime.now(),
                psycopg2.Binary(data),
                version,
                valid_from,
                valid_to,
                street_id
            ))
            
        id = cur.fetchone()[0]

    conn.commit()
    return id

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