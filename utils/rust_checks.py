""" Rust utils. """
from json import load, dump
from os import path as f_path

PATH = f_path.join(f_path.dirname(__file__))
CONFIG_PATH = f_path.join(PATH, "../config/rust-updates.json")


def load_rust_config(path=CONFIG_PATH):
    """ Load update dict. """
    if f_path.exists(path):
        with open(path) as conf_file:
            rust_config = load(conf_file)
    else:
        print("No Rust update config located, creating with defaults.")
        rust_config = {
            "channel": 1234567890
        }
        with open(path, "w+") as conf_file:
            dump(rust_config, conf_file, indent=4)
    return rust_config


RUST_CONFIG = load_rust_config()


def save_rust_config(rust_config: dict, path=CONFIG_PATH):
    """ Save the Rust config. """
    with open(path, "w+") as conf_path:
        dump(rust_config, conf_path, indent=4)
    return True
