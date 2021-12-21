import requests
import os
import wget
from bs4 import BeautifulSoup

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
last_file_downloaded = 0
if num > last_file_downloaded:
    wget.download(f"{url}{last_file_name}", os.path.join(os.getcwd(), last_file_name))
