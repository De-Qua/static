import yaml
import os


def update_yaml(logger, file_name="files_names.yaml", **kwargs):

    with open(os.path.join(os.getcwd(), file_name), 'r') as f:
        yaml_dict = yaml.load(f, Loader=yaml.FullLoader)
    for key in kwargs.keys():
        if key in yaml_dict.keys():
            yaml_dict[key] = kwargs[key]

    with open(os.path.join(os.getcwd(), file_name), 'w') as f:
        _ = yaml.dump(yaml_dict, f)

    return True
