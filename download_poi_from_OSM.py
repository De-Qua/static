import utils.library_overpass as lib_over
import pdb
import json
from datetime import datetime, timedelta

# venezia
bbox_venezia = [45.36, 12.32, 45.47, 12.41]
osm_id_venezia = 44741

import os
output = os.path.join('files', 'poi')
os.makedirs(output, exist_ok=True)

# when to download again
tolerance_secs = 60 * 60 * 24 * 7 # 1 week

total_poi = 0
#filters = ["'operator'='ACTV'"]
filter_tags = ["'amenity'", "'building'", "'boundary'", "'craft'", "'emergency'", "'healthcare'", \
               "'highway'", "'historic'", "'landuse'", "'leisure'", "'natural'", \
               "'office'", "'place'", "'power'", "'public_transport'", "'railway'", \
               "'route'", "'shop'", "'tourism'", "'water'", "'waterway'", "'addr:housenumber'", \
               "'addr:street'" ]
for filter_tag in filter_tags:
    #pdb.set_trace()
    tag = filter_tag[1:-1]
    target_path = os.path.join(output, f'{tag}.json')
    should_it_be_downloaded = False
    if not os.path.exists(target_path):
        should_it_be_downloaded = True
    else:
        with open(target_path, 'r') as dpoi:
            downloaded = json.load(dpoi)
        when = datetime.strptime(downloaded['osm3s']['timestamp_osm_base'], '%Y-%d-%mT%H:%M:%SZ')
        if (datetime.now() - when).seconds > tolerance_secs:
            print(f"downloading again {filter_tag}, already downloaded, but too old")
            should_it_be_downloaded = True
        else:
            print(f"skipping {filter_tag}, already downloaded and quite recent")
    if should_it_be_downloaded:
        cur_tags_poi = lib_over.download_data(osm_id_venezia, [filter_tag], what='all')
        print(f"Found {len(cur_tags_poi['elements'])} {tag}")
        lib_over.save_data_as(cur_tags_poi, target_path)
        total_poi += len(cur_tags_poi['elements'])

print(f"Finished downloading {total_poi} POIs")
