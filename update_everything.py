import os
import logging
from dequa_graph.utils import load_graphs, get_all_coordinates, add_waterbus_to_street

from logging.handlers import RotatingFileHandler
from update_actv_data import update_actv_data
from update_yaml import update_yaml
import yaml

yaml_file_name="files_names.yaml"
with open(os.path.join(os.getcwd(), yaml_file_name), 'r') as f:
    yaml_dict_old = yaml.load(f, Loader=yaml.FullLoader)

# add handler for files
if not os.path.exists('logs'):
    os.mkdir('logs')

logger = logging.getLogger('update')
logger.setLevel(logging.DEBUG)
file_handler = RotatingFileHandler('logs/automatic_tasks.log', maxBytes=100000, backupCount=10)
formatter = logging.Formatter('[%(asctime)s] [%(name)s:%(filename)s:%(lineno)d] [%(levelname)s] %(message)s')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)
yaml_dict_to_update = {}
# UPDATE ACTV
zip_name = "actv_nav.zip"
last_num = update_actv_data(logger, file_name=zip_name)
# UPDATE POI

if last_num > 0:
    yaml_dict_to_update['gtfs_last_number'] = last_num

    ## UPDATE GRAPHS
    logger.info("Loading the graphs...")
    graph_street, graph_water = load_graphs(yaml_dict_old['graph_street_file'], yaml_dict_old['graph_water_file'])
    path_zip_gtfs_actv = os.path.join(os.getcwd(), zip_name)
    logger.info("Adding waterbus to the graph...")
    graph_street_only, graph_street_street_plus_waterbus = add_waterbus_to_street(graph_street, path_zip_gtfs_actv)
    yaml_dict_to_update['graph_street_plus_waterbus_file'] = graph_street_street_plus_waterbus
    yaml_dict_to_update['graph_street_only_file'] = graph_street_only

if yaml_dict_to_update:
    update_yaml(logger, **yaml_dict_to_update)
