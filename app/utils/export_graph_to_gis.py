#!/usr/bin/env python
"""Export a graph_tool .gt graph to a GeoPackage (vertices + edges layers) readable by QGIS.

Usage:
    python export_graph_to_gis.py path/to/graph.gt path/to/output.gpkg
"""
import argparse
import json

import geopandas as gpd
import numpy as np
from geopandas.array import GeometryArray
from graph_tool import load_graph
from shapely.geometry import LineString, MultiLineString, Point

CRS = "EPSG:4326"
SCALAR_TYPES = {"bool", "short", "int16_t", "int32_t", "int64_t", "int",
                "long", "double", "float", "string"}


def _native(value):
    return value.item() if hasattr(value, "item") else value


def _serialize(value):
    """Turn dict/vector property values into JSON strings for the GIS attribute table."""
    if value is None:
        return None
    if isinstance(value, dict):
        return json.dumps({k: _native(v) for k, v in value.items()}, default=str)
    try:
        return json.dumps([_native(x) for x in value], default=str)
    except TypeError:
        return str(value)


def _sanitize_column(name):
    # GPKG/OGR field names should not start with a digit or contain dashes
    name = name.replace("-", "_")
    if name[0].isdigit():
        name = "d_" + name
    return name


def _to_multilinestring(geom):
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, LineString):
        return MultiLineString([geom])
    return geom


def _make_geodataframe(rows):
    # Built via GeometryArray (not gpd.GeoDataFrame(..., geometry=...)) because
    # geopandas 0.11 + shapely 1.7 crash when a plain list mixing Multi*
    # geometries with None goes through GeoSeries/from_shapely's numpy
    # slice-assignment path (NotImplementedError: Multi-part geometries do
    # not themselves provide the array interface).
    geoms = [row.pop("geometry") for row in rows]
    arr = np.empty(len(geoms), dtype=object)
    for i, geom in enumerate(geoms):
        arr[i] = geom
    gdf = gpd.GeoDataFrame(rows)
    gdf["geometry"] = GeometryArray(arr, crs=CRS)
    return gdf.set_geometry("geometry")


def export_graph(gt_path, out_path):
    g = load_graph(gt_path)

    vertex_rows = []
    for v in g.vertices():
        row = {"vertex_id": int(v)}
        for name, pmap in g.vp.items():
            if name == "latlon":
                continue
            value = pmap[v]
            col = _sanitize_column(name)
            row[col] = value if pmap.value_type() in SCALAR_TYPES else _serialize(value)
        lon, lat = g.vp["latlon"][v]
        row["geometry"] = Point(lon, lat)
        vertex_rows.append(row)
    vertices_gdf = _make_geodataframe(vertex_rows)

    edge_rows = []
    for e in g.edges():
        row = {
            "edge_id": int(g.edge_index[e]),
            "src": int(e.source()),
            "dst": int(e.target()),
        }
        geometry = None
        for name, pmap in g.ep.items():
            value = pmap[e]
            if name == "geometry":
                geometry = value
                continue
            col = _sanitize_column(name)
            row[col] = value if pmap.value_type() in SCALAR_TYPES else _serialize(value)
        row["geometry"] = _to_multilinestring(geometry)
        edge_rows.append(row)
    edges_gdf = _make_geodataframe(edge_rows)

    n_missing = edges_gdf["geometry"].isna().sum()
    if n_missing:
        print(f"Warning: {n_missing} edges have no geometry and will be written with a null geometry")

    vertices_gdf.to_file(out_path, layer="vertices", driver="GPKG")
    edges_gdf.to_file(out_path, layer="edges", driver="GPKG")
    print(f"Wrote {len(vertices_gdf)} vertices and {len(edges_gdf)} edges to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gt_path", help="Path to the input .gt graph_tool file")
    parser.add_argument("out_path", help="Path to the output .gpkg file")
    args = parser.parse_args()
    export_graph(args.gt_path, args.out_path)
