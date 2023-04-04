import utils.library_overpass as lib_over
import pdb

# venezia
bbox_venezia = [45.36, 12.32, 45.47, 12.41]
osm_id_venezia = 44741

import os
output = os.path.join('files', 'poi')
os.makedirs(output, exist_ok=True)

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
    if not os.path.exists(target_path):
        cur_tags_poi = lib_over.download_data(osm_id_venezia, [filter_tag], what='all')
        print(f"Found {len(cur_tags_poi['elements'])} {tag}")
        lib_over.save_data_as(cur_tags_poi, target_path)
        total_poi += len(cur_tags_poi['elements'])
    else:
        print(f"skipping {filter_tag}, already downloaded")

print(f"Finished downloading {total_poi} POIs")
