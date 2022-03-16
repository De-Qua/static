import yaml


def update_yaml(old_dict: dict, new_dict: dict, file_name: str):
    dict_to_save = old_dict | new_dict
    with open(file_name, 'w') as f:
        _ = yaml.dump(dict_to_save, f)
    return True

# def update_yaml(logger, file_name="files_names.yaml", **kwargs):
#
#     with open(os.path.join(os.getcwd(), file_name), 'r') as f:
#         yaml_dict = yaml.load(f, Loader=yaml.FullLoader)
#     for key in kwargs.keys():
#         if key in yaml_dict.keys():
#             yaml_dict[key] = kwargs[key]
#
#     with open(os.path.join(os.getcwd(), file_name), 'w') as f:
#         _ = yaml.dump(yaml_dict, f)
#
#     return True
