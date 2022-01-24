import os


def normalize(*parts):
    return os.path.normpath(os.path.join(*parts)).replace('\\', '/')
