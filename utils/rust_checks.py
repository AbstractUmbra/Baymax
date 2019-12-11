""" Rust utils. """
from json import load, dump
from os import path as f_path

PATH = f_path.join(f_path.dirname(__file__))


def load_rust_config(path="../config/rust-updates.json"):
    """ Load update dict. """
    actual_path = f_path.join(PATH, str(path))
    if f_path.exists(actual_path):
        with open(actual_path) as conf_file:
            rust_config = load(conf_file)
    else:
        print("No Rust update config located, creating with defaults.")
        rust_config = {
            "channel": 1234567890
        }
        with open(actual_path, "w+") as conf_file:
            dump(rust_config, conf_file, indent=4)
    return rust_config


def save_rust_config(rust_config: dict, path="../config/rust-updates.json"):
    """ Save the Rust config. """
    actual_path = f_path.join(PATH, str(path))
    with open(actual_path, "w+") as conf_path:
        dump(rust_config, conf_path, indent=4)
    return True
