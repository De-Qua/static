import os
import logging
from dequa_graph.utils import load_graphs, get_all_coordinates, add_waterbus_to_street

from logging.handlers import RotatingFileHandler
from update_actv_data import update_actv_data, get_updated_gtfs_files
from update_yaml import update_yaml
import yaml
import datetime
import ipdb


yaml_file_name = "files_names.yaml"
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
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.info("#" * 50)
logger.info("running the script")
yaml_dict_to_update = {}

file_folder = os.path.join(os.getcwd(), yaml_dict_old["file_folder"])
# UPDATE ACTV
gtfs_folder = os.path.join(file_folder, yaml_dict_old["gtfs_folder"])
zip_name = yaml_dict_old["gtfs_file"]
last_num = update_actv_data(logger, file_folder=gtfs_folder)
# UPDATE POI
start_date = datetime.date.today()


if last_num > 0:
    # ipdb.set_trace()
    path_zip_files_actv = get_updated_gtfs_files(logger, file_folder=gtfs_folder, start_date=start_date)
    yaml_dict_to_update['gtfs_last_number'] = last_num

    ## UPDATE GRAPHS
    logger.info("Loading the graphs...")
    graph_folder = os.path.join(file_folder, yaml_dict_old["graph_folder"])
    graph_street_path = os.path.join(graph_folder, yaml_dict_old['graph_street_file'])
    graph_water_path = os.path.join(graph_folder, yaml_dict_old['graph_water_file'])
    graph_street, graph_water = load_graphs(graph_street_path, graph_water_path)
    path_zip_gtfs_actv = os.path.join(file_folder, yaml_dict_old["gtfs_folder"], zip_name)
    logger.info("Adding waterbus to the graph...")
    graph_street_only, graph_street_street_plus_waterbus = add_waterbus_to_street(graph_street, path_zip_files_actv)
    today_time = datetime.datetime.today().strftime("%Y-%m-%d")

    new_graph_street_plus_waterbus_name = f"graph_street_plus_waterbus_file_{today_time}.gt"
    new_graph_street_plus_waterbus_path = os.path.join(graph_folder, new_graph_street_plus_waterbus_name)
    graph_street_street_plus_waterbus.save(new_graph_street_plus_waterbus_path)
    yaml_dict_to_update['graph_street_plus_waterbus_file'] = new_graph_street_plus_waterbus_name

    new_graph_street_only_name = f"graph_street_only_file_{today_time}.gt"
    new_graph_street_only_path = os.path.join(graph_folder, new_graph_street_only_name)
    graph_street_only.save(new_graph_street_only_path)
    yaml_dict_to_update['graph_street_only_file'] = new_graph_street_only_name

if yaml_dict_to_update:
    update_yaml(logger, **yaml_dict_to_update)
    logger.info("YAML updated")
else:
    logger.info("nothing to be updated")
