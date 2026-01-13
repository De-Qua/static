import utils.library_overpass as lib_over
import pdb
import json
from datetime import datetime, timedelta
import time 


######################
# DATA
osm_id_venezia = 44741
# when to download again
tolerance_days = 7 # 1 week
# complete list of tags
filter_tags = ["'amenity'", "'building'", "'boundary'", "'craft'", "'emergency'", "'healthcare'", \
               "'highway'", "'historic'", "'landuse'", "'leisure'", "'natural'", \
               "'office'", "'place'", "'power'", "'public_transport'", "'railway'", \
               "'route'", "'shop'", "'tourism'", "'water'", "'waterway'" ] #, "'addr:housenumber'", \

# folder structure
import os
output = os.path.join('files', 'poi')
os.makedirs(output, exist_ok=True)
output_logs = os.path.join('files', 'poi', 'logs')
os.makedirs(output_logs, exist_ok=True)
csv_output_logs = os.path.join(output, 'csv')
os.makedirs(csv_output_logs, exist_ok=True)

# sleep time between two queries
sleep_time = 5
# count how it goes
total_poi = 0
# we count the "tag" we downloaded
tags_downloaded_today = []
# and the ones which failed
errors_tags = []
# already there
tags_already_downloaded = []

timenow = datetime.now()

info_path = os.path.join(output_logs, f'log_{timenow.strftime("%Y-%m-%d")}.json')
reason_file_path = os.path.join(output_logs, f'log_{timenow.strftime("%Y-%m-%d")}.txt')

# for each tag, download POI and write to a json file
for filter_tag in filter_tags:

    tag = filter_tag[1:-1]
    target_path = os.path.join(output, f'{tag}.json')
    should_it_be_downloaded = False

    if not os.path.exists(target_path):
        print(f"no file with this tag {filter_tag}, let's download")
        should_it_be_downloaded = True
        when_last_download = None
    else:
        print('checking', target_path)
        with open(target_path, 'r') as dpoi:
            downloaded = json.load(dpoi)
        when_last_download = downloaded['osm3s']['timestamp_osm_base']
        time_last_download = datetime.strptime(when_last_download, '%Y-%m-%dT%H:%M:%SZ')
        period_from_last_time = (timenow - time_last_download)
        days_from_last_time = period_from_last_time.days
        # check if it's too old
        if days_from_last_time >= tolerance_days:
            with open(reason_file_path, 'a') as f:
                f.write(f"downloading again {filter_tag}, already downloaded on {time_last_download}, but too old\n")
            print(f"downloading again {filter_tag}, already downloaded, but too old")
            should_it_be_downloaded = True
        else:
            with open(reason_file_path, 'a') as f:
                f.write(f"skipping {filter_tag}, already downloaded and quite recent\n")
                f.write(f"period from last time {period_from_last_time}\nIn days: {days_from_last_time}\n")
            print(f"skipping {filter_tag}, already downloaded and quite recent")
            tags_already_downloaded.append(filter_tag)
    
    ###############################3
    # here download the new data
    if should_it_be_downloaded:
        cur_tags_poi = lib_over.download_data(osm_id_venezia, [filter_tag], what='all', newer_than=when_last_download)
        
        if cur_tags_poi is not None:
            tags_downloaded_today.append(filter_tag)
            print(f"Found and downloaded {len(cur_tags_poi['elements'])} POIs with tag={tag}")
            lib_over.save_data_as(cur_tags_poi, target_path)
            csv_path = os.path.join(csv_output_logs, f'{tag}.csv')
            lib_over.save_data_as(cur_tags_poi, csv_path, format='csv')
            total_poi += len(cur_tags_poi['elements'])
            last_download_date = timenow
        else:
            print(f"Error while downloading POIs with tag={tag}")
            errors_tags.append(filter_tag)
    else:
        last_download_date = time_last_download

    # wait a couple of seconds
    time.sleep(sleep_time)

# dump some info in the .json file
download_info = {
    'last_download':last_download_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
    'tags_already_downloaded': tags_already_downloaded,
    'tags_downloaded_today': tags_downloaded_today,
    'errors_tags': errors_tags,
    'downloaded_poi': total_poi,
    'all_tags': filter_tags
}
with open(info_path, 'a') as log_json:
    json.dump(download_info, log_json, indent=2)


with open(reason_file_path, 'a') as f:
    f.write(f"Finished downloading {total_poi} POIs\nDownloaded {len(tags_downloaded_today)}/{len(filter_tags)} tags\n")
    f.write("-" * 50)
    f.write(f"\nAlready there: \n")
    for ftag in tags_already_downloaded:
        f.write(f" - {ftag}\n")
    f.write(f"Downloaded today: \n")
    for ftag in tags_downloaded_today:
        f.write(f" - {ftag}\n")
    f.write(f"Errors: \n")
    for ftag in errors_tags:
        f.write(f" - {ftag}\n")
    f.write("-" * 50)