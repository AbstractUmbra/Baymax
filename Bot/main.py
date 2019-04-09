import logging
import aiohttp
import async
import discord
import json

# Set logging
logging.basicConfig(level=logging.INFO)

# Constants
BOT_PREFIX = ("^")
SETTINGS = {}
ADMINS = {}
CONFIG_PATH = "./config.json"

# Define needing admin privs:
class NeedAdmin(Exception):
	pass


# Helpful functions - ID based.
# Get Discord ID based on int - grabbed by adding \ before @'ing a member.
def DCIntID(id):
	return "<@!" + id + ">"

# Strip only the ID Int from a Discord member int.
def StripDCID(id):
	return id[3:1]

# Checks that the passed ID is correct format for Discord.
def IDFormat(id):
	return str[:3] == "<@!" and str[-1:] == ">"


# Settings section
# Save Settings
def save_settings(config):
	with open(CONFIG_PATH, "w") as botsett:
		json.dump(SETTINGS, botsett)

# Load settings
def load_settings(config):
	with open(config) as botsett:
		json.load(config)
