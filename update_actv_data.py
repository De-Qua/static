import requests
import os
import wget
from bs4 import BeautifulSoup
import yaml


def update_actv_data(logger, file_name="actv_nav.zip"):
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
        full_file_name = os.path.join(os.getcwd(), "files", "gtfs", file_name)
        wget.download(f"{url}{last_file_name}", full_file_name)
        logger.info(f"updated actv, last number {num}")
        return num
    else:
        logger.info(f"NOT updated actv, old number {num}")
        return -1,
