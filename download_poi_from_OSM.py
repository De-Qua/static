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
tolerance_days = 0 # 1 week

total_poi = 0
downloaded_tags = []
#filters = ["'operator'='ACTV'"]
filter_tags = ["'amenity'", "'building'", "'boundary'", "'craft'", "'emergency'", "'healthcare'", \
               "'highway'", "'historic'", "'landuse'", "'leisure'", "'natural'", \
               "'office'", "'place'", "'power'", "'public_transport'", "'railway'", \
               "'route'", "'shop'", "'tourism'", "'water'", "'waterway'" ] #, "'addr:housenumber'", \
            #    "'addr:street'" ]

output_logs = os.path.join('files', 'poi', 'logs')
os.makedirs(output_logs, exist_ok=True)
timenow = datetime.now()
info_path = os.path.join(output_logs, f'log_{timenow.strftime("%Y-%m-%d")}.json')
reason_file_path = os.path.join(output_logs, f'log_{timenow.strftime("%Y-%m-%d")}.txt')
for filter_tag in filter_tags:
    #pdb.set_trace()
    tag = filter_tag[1:-1]
    target_path = os.path.join(output, f'{tag}.json')
    should_it_be_downloaded = False
    if not os.path.exists(target_path):
        should_it_be_downloaded = True
        when_last_download = None
    else:
        print('checking ', target_path)
        with open(target_path, 'r') as dpoi:
            downloaded = json.load(dpoi)
        when_last_download = downloaded['osm3s']['timestamp_osm_base']
        when = datetime.strptime(when_last_download, '%Y-%m-%dT%H:%M:%SZ')
        # timenow = datetime.now()
        period_from_last_time = (timenow - when)
        days_from_last_time = period_from_last_time.days
        if days_from_last_time > tolerance_days:
            with open(reason_file_path, 'a') as f:
                f.write(f"downloading again {filter_tag}, already downloaded on {when}, but too old\n")
            print(f"downloading again {filter_tag}, already downloaded, but too old")
            should_it_be_downloaded = True
        else:
            with open(reason_file_path, 'a') as f:
                f.write(f"skipping {filter_tag}, already downloaded and quite recent\n")
                f.write(f"period from last time {period_from_last_time}\nIn days: {days_from_last_time}\n")
            print(f"skipping {filter_tag}, already downloaded and quite recent")
    if should_it_be_downloaded:
        cur_tags_poi = lib_over.download_data(osm_id_venezia, [filter_tag], what='all', newer_than=when_last_download)
        downloaded_tags.append(filter_tag)
        print(f"Found {len(cur_tags_poi['elements'])} {tag}")
        lib_over.save_data_as(cur_tags_poi, target_path)
        total_poi += len(cur_tags_poi['elements'])
        last_download_date = timenow
    else:
        last_download_date = when

download_info = {
    'last_download':last_download_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
    'downloaded_tags': downloaded_tags,
    'downloaded_poi': total_poi,
    'all_tags': filter_tags
}


with open(info_path, 'a') as log_json:
    json.dump(download_info, log_json, indent=2)
print(f"Finished downloading {total_poi} POIs")
