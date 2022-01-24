import os


this_path = os.path.dirname(__file__)


def get_path(resource):
    return os.path.join(this_path, resource).replace('\\', '/')


def get_icon_variables():
    data = {}
    for file in os.listdir(this_path):
        if file.endswith('.png'):
            data[os.path.splitext(file)[0]] = get_path(file)
    return data
