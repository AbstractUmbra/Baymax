""" Automod utils. """
from json import load, dump
from os import path as f_path

PATH = f_path.join(f_path.dirname(__file__))
BANNED_PATH = f_path.join(PATH, "../config/banned.json")
MUTED_PATH = f_path.join(PATH, "../config/muted.json")


def load_bans(path=BANNED_PATH):
    """ Load ban dict. """
    if f_path.exists(path):
        with open(path) as ban_file:
            banned_users = load(ban_file)
    else:
        print("No ban config found. Creating defaults")
        banned_users = {
            "user": 123456789012345678790
        }
        with open(path, "w+") as ban_file:
            dump(banned_users, ban_file, indent=4)
    return banned_users


def load_mutes(path=MUTED_PATH):
    """ Load mute dict. """
    if f_path.exists(path):
        with open(path) as mute_file:
            muted_users = load(mute_file)
    else:
        print("No mute config found. Creating defaults")
        muted_users = {
            "user": 123456789012345678790
        }
        with open(path, "w+") as mute_file:
            dump(muted_users, mute_file, indent=4)
    return muted_users


MUTED_USERS = load_mutes()
BANNED_USERS = load_bans()


def save_bans(ban_dict: dict, path=BANNED_PATH):
    """ Save ban dict. """
    with open(path, "w") as ban_path:
        dump(ban_dict, ban_path, indent=4)
    return True


def save_mute(mute_dict: dict, path=MUTED_PATH):
    """ Save mute dict. """
    with open(path, "w") as mute_path:
        dump(mute_dict, mute_path, indent=4)
    return True
