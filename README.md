# Robo-Hz

A personal bot for Discord, written with love and fun.

## Running

First things first: I would prefer (and will not support) you running instances of my Bot. Just call the `join` command and invite it to your server.

Nevertheless; installation steps are below.

### Installation
1. Install Python 3.6.0 or higher.
2. Set up a venv (of any flavour)
   1. `python -m venv myvenv`
3. Install required dependencies
   1. `pip install -U -r requirements.txt`
4. Create the database in PostgreSQL
   ```sql
   CREATE ROLE robohz WITH LOGIN PASSWORD 'mypasswd';
   CREATE DATABASE robohz OWNER robohz;
   CREATE EXTENSION pg_trgm;
    ```
5. Set up configuration.
   1. There is an example `config.py` in the repo. Please replace the values in there with your actual values.
6. Configure the database.
   1. `python launcher.py db init`


## Requirements

    - Python 3.6+
    - PostgreSQL server/access with a minimum of v9
    - Minimum of Discord.py v1.3.0
    - Modules within `requirements.txt`