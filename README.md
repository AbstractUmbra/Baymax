# Akane

A personal bot for Discord, written with love and fun.

Originally a fork of [RoboDanny](https://github.com/Rapptz/RoboDanny) with some edits.

## Running

First things first: I would prefer (and will not support) you running instances of my Bot.

As such, the setup of my config file is not public.

Nevertheless; installation steps are below.

### Installation
1. Install Python 3.9.1 or higher.
2. Set up a venv (of any flavour)
    1. I use `poetry` hence the `pyproject.toml` and `poetry.lock`
3. Install required dependencies
4. Create the database in PostgreSQL
   ```sql
   CREATE ROLE akane WITH LOGIN PASSWORD 'mypasswd';
   CREATE DATABASE akane OWNER Akane;
   CREATE EXTENSION pg_trgm;
    ```
5. Set up configuration.
6. Configure the database.
   1. `python launcher.py db init`


## Requirements

    - Python 3.9+
    - PostgreSQL server/access with a minimum of v9
    - Minimum version of Discord.py v1.6.0
    - Modules within `pyproject.toml`