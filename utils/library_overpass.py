import requests
import json
import numpy as np
import matplotlib.pyplot as plt# Collect coords into list
import datetime as dt
import csv 

def download_data(bbox, filters, what='nodes', newer_than=None, 
                timeout=30, overpass_url = "http://overpass-api.de/api/interpreter"):
    if not newer_than:
        newer_than = "1900-01-01T01:01:00Z"
    
    overpass_query = """
    [out:json];
    """
    if type(bbox) is list:
        overpass_query += """("""
        # convert list in string without [ ]
        bbox_query = str(bbox)[1:-1]
    elif type(bbox is int):
        overpass_query += f"relation   ({bbox}) -> .c ; \
        .c map_to_area -> .myarea ; \
        ( "
        # set the new object as bbox
        bbox_query = "area.myarea"
    if what == 'nodes':
        for filter in filters:
            overpass_query += "\n"
            overpass_query += f'node[{filter}](newer:"{newer_than}")({bbox_query});'
    elif what == 'ways':
        for filter in filters:
            overpass_query += "\n"
            overpass_query += f'way[{filter}](newer:"{newer_than}")({bbox_query});'
    elif what == 'relations':
        for filter in filters:
            overpass_query += "\n"
            overpass_query += f'relation[{filter}](newer:"{newer_than}")({bbox_query});'
    elif what == 'all':
        for filter in filters:
            overpass_query += "\n"
            overpass_query += f'node[{filter}](newer:"{newer_than}")({bbox_query}); \
            way[{filter}](newer:"{newer_than}")({bbox_query}); \
            relation[{filter}](newer:"{newer_than}")({bbox_query});'

    overpass_query += """
    );
    out center;
    """
    print(f"Overpass query:\n{overpass_query}\n")

    # response = requests.get(overpass_url,params={'data': overpass_query})
    # data = response.json()

    # if we want to be polite
    # and write down who we are
    headers = {
        'User-Agent': 'YourProjectName/1.0 (your@email.com)',
        'Accept': 'application/json'
    }

    try:
        response = requests.get(
            overpass_url,
            params={'data': overpass_query},
            # headers=headers,
            timeout=timeout
        )
        data = response.json()

        # response.raise_for_status()
        # return response.json() if output_format == "json" else response.text

    except Exception as e:
        print(f"Error during download of {filters[0]}: {e}")
        return None

    return data

def save_data_as(data, path, format='json'):

    if format == 'csv':
        if path.endswith('.json'):
            path = path[:-4]+'csv'
        export_to_csv(data, path)
    else:
        with open(path, 'w') as outfile:
            json.dump(data, outfile)

def export_to_csv(data, path):

    elements = data.get('elements', [])
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Header
        writer.writerow([
            "id", "type", "name", "category", "lat", "lon", "last_modified", "tags"
        ])
        for elem in elements:
            elem_id = elem.get('id', '')
            elem_type = elem.get('type', '')
            name = elem.get('tags', {}).get('name', '')
            category = elem.get('tags', {}).get('amenity', elem.get('tags', {}).get('shop', ''))
            lat = elem.get('lat', elem.get('center', {}).get('lat', ''))
            lon = elem.get('lon', elem.get('center', {}).get('lon', ''))
            last_modified = elem.get('timestamp', '')  # Not always available
            tags = str(elem.get('tags', {}))
            writer.writerow([elem_id, elem_type, name, category, lat, lon, last_modified, tags])
    print(f"Exported to {path}")

def remove_headers_and_tolist(data):

    values_data = data.values()
    return list(values_data)[3]

def show_us_how_one_node_look_like(data):

    values_data = data.values()
    print(values_data[0])


def draw_the_data(data, titlePlot):

    coords = []
    for element in data['elements']:
      if element['type'] == 'node':
        lon = element['lon']
        lat = element['lat']
        coords.append((lon, lat))
      elif 'center' in element:
        lon = element['center']['lon']
        lat = element['center']['lat']
        coords.append((lon, lat))# Convert coordinates into numpy array
    X = np.array(coords)
    plt.plot(X[:, 0], X[:, 1], 'o')
    plt.title(titlePlot)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.axis('equal')
    plt.show()
