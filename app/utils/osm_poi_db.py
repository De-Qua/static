"""
Store the POIs converted from OSM (see osm_poi_mapping) in the opendata database.
"""
import datetime
import logging
from collections import Counter

import geoalchemy2  # registers the Geometry type used when reflecting the tables
from geoalchemy2.shape import to_shape
from shapely.geometry import Point
from shapely.prepared import prep
from sqlalchemy import create_engine, delete, exists, func, insert, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

from utils.osm_poi_mapping import COLUMN_TAGS

logger = logging.getLogger("dequa_update_poi.poi_db")

# Geometry columns have no SRID (plain lon/lat)
SRID = 0
# Max distance (m) between a POI and the closest location with a house number
MAX_ADDRESS_DIST_M = 50
# Tables used by the script (only these are reflected)
TABLES = ["poi", "poi_name", "poi_types", "poi_category", "poi_category_type",
          "location", "address", "neighborhood"]
# poi columns filled from the OSM tags
POI_COLUMNS = sorted(set(COLUMN_TAGS.values()))
# Results of store_poi that mean the POI is in the database
STORED_RESULTS = {"inserted", "updated", "unchanged"}


class PoiDatabase:

    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        base = automap_base()
        base.metadata.reflect(self.engine, only=TABLES)
        base.prepare()
        self.Poi = base.classes.poi
        self.PoiName = base.classes.poi_name
        self.PoiCategory = base.classes.poi_category
        self.PoiCategoryType = base.classes.poi_category_type
        self.Location = base.classes.location
        self.Address = base.classes.address
        self.Neighborhood = base.classes.neighborhood
        self.poi_types = base.metadata.tables["poi_types"]
        # Max length of the string columns, used to truncate the OSM values
        self.max_lengths = {
            table.name: {c.name: c.type.length for c in table.columns if getattr(c.type, "length", None)}
            for table in (self.Poi.__table__, self.PoiName.__table__, self.PoiCategory.__table__,
                          self.PoiCategoryType.__table__)
        }

    def truncate(self, table, column, value):
        max_length = self.max_lengths[table].get(column)
        if isinstance(value, str) and max_length and len(value) > max_length:
            return value[:max_length]
        return value

    # ---------------------------------------------------------------- load

    def load(self, pois, reset=False):
        """
        Insert or update the POIs in a single transaction: users see the old data until the commit.
        reset=True deletes all the POIs, categories and types before loading.
        Returns a Counter with the results.
        """
        stats = Counter()
        now = datetime.datetime.now()
        with Session(self.engine) as session, session.begin():
            if reset:
                self.delete_all_pois(session)
            neighborhoods = self.load_neighborhoods(session)
            existing = {(p.osm_type, p.osm_id): p
                        for p in session.query(self.Poi).filter(self.Poi.osm_id.isnot(None))}
            categories = {c.name: c for c in session.query(self.PoiCategory)}
            types = {(t.category_id, t.name): t for t in session.query(self.PoiCategoryType)}

            stored = set()
            for osm_poi in pois:
                key = (osm_poi.osm_type, osm_poi.osm_id)
                try:
                    # Categories and types are created outside the savepoint: they are cached and reused
                    type_ids = self.get_or_create_types(session, osm_poi.categories, categories, types)
                    # Savepoint: an error on a POI does not roll back the others
                    with session.begin_nested():
                        result = self.store_poi(session, osm_poi, existing.get(key), neighborhoods, type_ids, now)
                except Exception:
                    logger.exception(f"Error storing {osm_poi.osm_type}/{osm_poi.osm_id}")
                    result = "error"
                stats[result] += 1
                if result in STORED_RESULTS:
                    stored.add(key)

            if not reset:
                stats["deleted"] = self.delete_missing(session, existing, stored)
            stats["deleted_locations"] = self.delete_orphan_locations(session)

        logger.info(f"POIs loaded: {dict(stats)}")
        return stats

    def store_poi(self, session, osm_poi, poi, neighborhoods, type_ids, now):
        """Insert or update a POI. Returns inserted/updated/unchanged or the reason why it was skipped."""
        location_id, reason = self.get_location_id(session, osm_poi, neighborhoods)
        if reason:
            return reason

        values = {column: self.truncate("poi", column, osm_poi.columns.get(column)) for column in POI_COLUMNS}
        values.update(osm_type=osm_poi.osm_type, osm_id=osm_poi.osm_id,
                      location_id=location_id, osm_tags=osm_poi.osm_tags)

        if poi is None:
            # score and last_change have no default in the database
            poi = self.Poi(score=0, last_change=now, **values)
            session.add(poi)
            session.flush()
            result = "inserted"
        else:
            changed = {k: v for k, v in values.items() if getattr(poi, k) != v}
            for k, v in changed.items():
                setattr(poi, k, v)
            result = "updated" if changed else "unchanged"

        types_changed = self.sync_types(session, poi.id, type_ids)
        names_changed = self.sync_names(session, poi.id, osm_poi.names)
        if result == "unchanged" and (types_changed or names_changed):
            result = "updated"
        if result == "updated":
            poi.last_change = now
        return result

    # ------------------------------------------------------------ location

    def load_neighborhoods(self, session):
        """Neighborhood shapes as prepared shapely geometries (fast point-in-polygon checks)."""
        return [prep(to_shape(n.shape)) for n in session.query(self.Neighborhood)]

    def get_location_id(self, session, osm_poi, neighborhoods):
        """Returns (location_id, None) or (None, reason) when the POI must be skipped."""
        point = Point(osm_poi.lon, osm_poi.lat)
        if not any(n.contains(point) for n in neighborhoods):
            return None, "outside"

        # POIs without a house number (fountains, benches, ...): location at their own coordinates
        if osm_poi.standalone_location:
            location = (session.query(self.Location)
                        .filter_by(latitude=osm_poi.lat, longitude=osm_poi.lon).first())
            return (location.id if location else self.create_location(session, point)), None

        # Otherwise the closest location with a house number
        geom = func.ST_GeomFromText(point.wkt, SRID)
        has_address = exists().where(self.Address.location_id == self.Location.id)
        closest = (session.query(self.Location.id, func.ST_DistanceSphere(self.Location.shape, geom))
                   .filter(has_address)
                   .order_by(self.Location.shape.distance_centroid(geom))
                   .first())
        if closest and closest[1] <= MAX_ADDRESS_DIST_M:
            return closest[0], None
        # Far from any address: keep it with its own location only if it has a name
        if osm_poi.columns.get("name"):
            return self.create_location(session, point), None
        return None, "no_name"

    def create_location(self, session, point):
        location = self.Location(latitude=point.y, longitude=point.x,
                                 shape=func.ST_GeomFromText(point.wkt, SRID))
        session.add(location)
        session.flush()
        return location.id

    # --------------------------------------------------- categories, types

    def get_or_create_types(self, session, poi_categories, categories, types):
        """Ids of the (category, type) pairs, creating the missing ones."""
        type_ids = []
        for category_name, type_name in poi_categories:
            category_name = self.truncate("poi_category", "name", category_name)
            type_name = self.truncate("poi_category_type", "name", type_name)
            category = categories.get(category_name)
            if category is None:
                category = self.PoiCategory(name=category_name)
                session.add(category)
                session.flush()
                categories[category_name] = category
            poi_type = types.get((category.id, type_name))
            if poi_type is None:
                poi_type = self.PoiCategoryType(name=type_name, category_id=category.id)
                session.add(poi_type)
                session.flush()
                types[(category.id, type_name)] = poi_type
            if poi_type.id not in type_ids:
                type_ids.append(poi_type.id)
        return type_ids

    def sync_types(self, session, poi_id, type_ids):
        """Make poi_types match type_ids. Returns True if something changed."""
        current = set(session.execute(
            select(self.poi_types.c.type_id).where(self.poi_types.c.poi_id == poi_id)).scalars())
        new = set(type_ids)
        if current == new:
            return False
        if current - new:
            session.execute(delete(self.poi_types).where(self.poi_types.c.poi_id == poi_id,
                                                         self.poi_types.c.type_id.in_(current - new)))
        if new - current:
            session.execute(insert(self.poi_types),
                            [{"poi_id": poi_id, "type_id": type_id} for type_id in new - current])
        return True

    def sync_names(self, session, poi_id, names):
        """Make poi_name match the alternative names. Returns True if something changed."""
        new = {(self.truncate("poi_name", "name", name), kind, lang) for name, kind, lang in names}
        current = {(n.name, n.kind, n.lang) for n in session.query(self.PoiName).filter_by(poi_id=poi_id)}
        if current == new:
            return False
        session.query(self.PoiName).filter_by(poi_id=poi_id).delete()
        session.add_all(self.PoiName(poi_id=poi_id, name=name, kind=kind, lang=lang) for name, kind, lang in new)
        return True

    # ------------------------------------------------------------ deletion

    def delete_all_pois(self, session):
        # poi_types and poi_name rows are deleted by ON DELETE CASCADE
        deleted = session.execute(delete(self.Poi.__table__)).rowcount
        session.execute(delete(self.PoiCategoryType.__table__))
        session.execute(delete(self.PoiCategory.__table__))
        logger.info(f"Reset: deleted {deleted} POIs with all categories and types")

    def delete_missing(self, session, existing, stored):
        """Delete the OSM POIs that are no longer in OSM (or no longer valid)."""
        missing_ids = [poi.id for key, poi in existing.items() if key not in stored]
        if missing_ids:
            session.execute(delete(self.Poi.__table__).where(self.Poi.id.in_(missing_ids)))
        return len(missing_ids)

    def delete_orphan_locations(self, session):
        """Delete the locations without address and without POIs (e.g. created for deleted POIs)."""
        L, A, P = self.Location, self.Address, self.Poi
        stmt = (delete(L.__table__)
                .where(~exists().where(A.location_id == L.id))
                .where(~exists().where(P.location_id == L.id)))
        return session.execute(stmt).rowcount
