import requests
import json
import numpy as np
import matplotlib.pyplot as plt# Collect coords into list
import datetime as dt

def download_data(bbox, filters, what='nodes', newer_than=None):
    if not newer_than:
        newer_than = "1900-01-01T01:01:00Z"
    overpass_url = "http://overpass-api.de/api/interpreter"
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
    print(overpass_query)
    response = requests.get(overpass_url,params={'data': overpass_query})
    data = response.json()

    return data

def save_data_as(data, path):

    with open(path, 'w') as outfile:
        json.dump(data, outfile)

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
