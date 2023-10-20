# Documentation

## Requirements

### packages

pip3 install sqlalchemy sqlalchemy_utils psycopg2

## Desriptions

### sql_alchemy.py

This script calls init_db.py to create the database and the table.
It self can create, update, find and remove entries from the database.

### init_db.py

This script contains a simple solution to create a database with a table based on a class.
It is working with a postgresql connection to a docker container.
