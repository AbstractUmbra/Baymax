""" Utility file addon - Settings. """

from os import path as fpath
from json import load, dump


PATH = fpath.join(fpath.dirname(__file__))
CONFIG_PATH = fpath.join(PATH, "../config/settings.json")


def load_settings(path=CONFIG_PATH):
    """ Load the settings from JSON. """
    if fpath.exists(path):
        with open(path) as config_file:
            settings = load(config_file)
    else:
        print(f"No settings file exists at {path}. Using defaults.")
        settings = {
            "admins": [],
            "bound_text_channels": [],
            "bot_description": "A generic use bot for fun, games and memes.",
            "bot_prefix": "^"
        }
        with open(path, "w+") as config_file:
            dump(settings, config_file, indent=4)
    return settings


SETTINGS = load_settings()


def save_settings(settings_dict: dict, path=CONFIG_PATH):
    """ Save settings in a passed config file. """
    with open(path, "w") as config_file:
        dump(settings_dict, config_file, indent=4)
    return True
