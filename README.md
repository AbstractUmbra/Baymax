# Robo-Hz

A personal bot for Discord, written with love and fun.

## Running

First things first: I would prefer (and will not support) you running instances of my Bot. Just call the `join` command and invite it to your server.

As such, the setup of my config file is not public.

Nevertheless; installation steps are below.

### Installation
1. Install Python 3.6.1 or higher.
2. Set up a venv (of any flavour)
   1. I prefer pipenv, so I have provided a Pipfile as well as a 'requirements.txt'
3. Install required dependencies
   1. `pipenv install` or `pip install -U -r requirements.txt`
4. Create the database in PostgreSQL
   ```sql
   CREATE ROLE robohz WITH LOGIN PASSWORD 'mypasswd';
   CREATE DATABASE robohz OWNER robohz;
   CREATE EXTENSION pg_trgm;
    ```
5. Set up configuration.
6. Configure the database.
   1. `python launcher.py db init`


## Requirements

    - Python 3.6.1+
    - PostgreSQL server/access with a minimum of v9
    - Minimum version of Discord.py v1.3.0
    - libgit2 install on host, or via pip.
    - Modules within `Pipfile` or `requirements.txt`