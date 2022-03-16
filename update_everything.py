import yaml
import datetime
import logging
from pathlib import Path

from dequa_graph.utils import load_graphs, add_waterbus_to_street

from utils.update_actv_data import get_updated_gtfs_files, get_last_actv_index, download_actv_data
from utils.update_yaml import update_yaml
from utils.logger import get_logger

# import ipdb

YAML_FILE_NAME = "files_names.yaml"


def main(logger):

    # Load the yaml file
    with open(Path(YAML_FILE_NAME), 'r') as f:
        yaml_dict_old = yaml.load(f, Loader=yaml.FullLoader)

    yaml_dict_to_update = {}

    # FOLDERS
    file_folder = Path(yaml_dict_old["file_folder"])
    # tide
    tide_folder = file_folder / yaml_dict_old["tide_folder"]
    tide_folder.mkdir(parents=True, exist_ok=True)
    # gtfs
    gtfs_folder = file_folder / yaml_dict_old["gtfs_folder"]
    gtfs_folder.mkdir(parents=True, exist_ok=True)
    # path_zip_gtfs_actv = file_folder / yaml_dict_old["gtfs_folder"] / yaml_dict_old["gtfs_file"]
    # graphs
    graph_folder = file_folder / yaml_dict_old["graph_folder"]
    graph_folder.mkdir(parents=True, exist_ok=True)
    graph_street_path = graph_folder / yaml_dict_old['graph_street_file']
    graph_water_path = graph_folder / yaml_dict_old['graph_water_file']

    # UPDATE ACTV
    last_num, last_data_name = get_last_actv_index()
    if last_num > yaml_dict_old["gtfs_last_number"]:
        logger.info(f"New ACTV file: {last_data_name}")
        logger.debug(f"Current index: {yaml_dict_old['gtfs_last_number']}")
        logger.debug(f"New index: {last_num}")
        # download the new file
        new_file = download_actv_data(last_data_name, gtfs_folder)
        logger.debug(f"Downloaded {new_file}")

        # update gtfs file
        start_date = datetime.date.today()
        path_zip_files_actv = get_updated_gtfs_files(logger, file_folder=gtfs_folder, start_date=start_date)

        # update the graphs
        logger.debug("Loading the graphs...")
        graph_street, graph_water = load_graphs(str(graph_street_path), str(graph_water_path))
        logger.debug("Adding waterbus to the graph...")
        graph_street_only, graph_street_street_plus_waterbus = add_waterbus_to_street(graph_street, path_zip_files_actv)

        # save the graphs
        today_time = datetime.datetime.today().strftime("%Y-%m-%d")

        new_graph_street_plus_waterbus_name = f"graph_street_plus_waterbus_file_{today_time}.gt"
        new_graph_street_plus_waterbus_path = graph_folder / new_graph_street_plus_waterbus_name
        graph_street_street_plus_waterbus.save(str(new_graph_street_plus_waterbus_path))

        new_graph_street_only_name = f"graph_street_only_file_{today_time}.gt"
        new_graph_street_only_path = graph_folder / new_graph_street_only_name
        graph_street_only.save(str(new_graph_street_only_path))

        # update yaml file
        yaml_dict_to_update['gtfs_last_number'] = last_num
        yaml_dict_to_update['graph_street_plus_waterbus_file'] = new_graph_street_plus_waterbus_name
        yaml_dict_to_update['graph_street_only_file'] = new_graph_street_only_name
        update_yaml(yaml_dict_old, yaml_dict_to_update, YAML_FILE_NAME)
        logger.info("New yaml file saved")
    else:
        logger.info("No update")


if __name__ == '__main__':
    # Get the logger
    logger = get_logger(name="dequa_update", file="logs/automatic_tasks.log", level=logging.DEBUG)

    logger.info("#" * 50)
    logger.info("running the script")
    main(logger)
# last_num = update_actv_data(logger, file_folder=gtfs_folder)
# # UPDATE POI
# start_date = datetime.date.today()
#
#
# if last_num > 0:
#     # ipdb.set_trace()
#     path_zip_files_actv = get_updated_gtfs_files(logger, file_folder=gtfs_folder, start_date=start_date)
#     yaml_dict_to_update['gtfs_last_number'] = last_num
#
#     ## UPDATE GRAPHS
#     logger.debug("Loading the graphs...")
#     graph_street, graph_water = load_graphs(graph_street_path, graph_water_path)
#     logger.info("Adding waterbus to the graph...")
#     graph_street_only, graph_street_street_plus_waterbus = add_waterbus_to_street(graph_street, path_zip_files_actv)
#     today_time = datetime.datetime.today().strftime("%Y-%m-%d")
#
#     new_graph_street_plus_waterbus_name = f"graph_street_plus_waterbus_file_{today_time}.gt"
#     new_graph_street_plus_waterbus_path = os.path.join(graph_folder, new_graph_street_plus_waterbus_name)
#     graph_street_street_plus_waterbus.save(new_graph_street_plus_waterbus_path)
#     yaml_dict_to_update['graph_street_plus_waterbus_file'] = new_graph_street_plus_waterbus_name
#
#     new_graph_street_only_name = f"graph_street_only_file_{today_time}.gt"
#     new_graph_street_only_path = os.path.join(graph_folder, new_graph_street_only_name)
#     graph_street_only.save(new_graph_street_only_path)
#     yaml_dict_to_update['graph_street_only_file'] = new_graph_street_only_name
#
# if yaml_dict_to_update:
#     update_yaml(logger, **yaml_dict_to_update)
#     logger.info("YAML updated")
# else:
#     logger.info("nothing to be updated")
