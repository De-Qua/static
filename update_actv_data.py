import requests
from datetime import date
import os
import pandas as pd
import glob
from bs4 import BeautifulSoup
import yaml
import gtfs_kit
import urllib


def update_actv_data(logger, file_folder=None):
    if file_folder is None:
        file_folder = os.path.join(os.getcwd(), "files", "gtfs")
    # get the page
    url = 'https://actv.avmspa.it/sites/default/files/attachments/opendata/navigazione/'
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    # get all links/files
    links = soup.find_all('a')
    # last one
    link = links[-1]
    # name of the zip file
    last_file_name = link.get('href')
    # number
    num_string = last_file_name.split('_')[-1][:-4]
    num = int(num_string)
    # read last one from yaml file
    with open('files_names.yaml') as f:
        variables = yaml.load(f, Loader=yaml.FullLoader)
    last_file_downloaded = variables['gtfs_last_number']
    if num > last_file_downloaded:
        full_file_name = os.path.join(file_folder, last_file_name)
        urllib.request.urlretrieve(f"{url}{last_file_name}", full_file_name)
        logger.info(f"updated actv, last number {num}")
        return num
    else:
        logger.info(f"NOT updated actv, old number {num}")
        return -1


def get_updated_gtfs_files(logger, file_folder=None, file_format="*.zip", start_date=None):
    if file_folder is None:
        file_folder = os.path.join(os.getcwd(), "files", "gtfs")
    if start_date is None:
        start_date = date.today()
    # check all the files that match with file format
    files = [f for f in glob.glob(os.path.join(file_folder, file_format))]
    updated_files = []
    for file in files:
        try:
            feed = gtfs_kit.read_feed(file, dist_units="km")
            last_date = pd.to_datetime(feed.calendar["end_date"]).max()
            if last_date < start_date:
                os.remove(file)
                logger.info(f"Removed GTFS file with last_date {last_date}: {file}")
            else:
                updated_files.append(file)
                logger.debug(f"GTFS file: {file}")
        except Exception as e:
            logger.warning(f"Reading GTFS file exception: {e}")
    return updated_files
