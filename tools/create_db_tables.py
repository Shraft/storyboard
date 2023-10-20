from sqlalchemy import create_engine, Column
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.sqltypes import String, Integer, DateTime, Boolean
from sqlalchemy_utils import database_exists, create_database
import psycopg2


def create_user_db():

    # CREATE USER DB -----------------------------------------------------------------------------
    db_string = "postgresql://python:example@localhost:5432/user_db"
    engine = create_engine(db_string)


    # Create database if it does not exist.
    if database_exists(engine.url):
        print("UserDB already exists")
        return

    create_database(engine.url)
    print("UserDB created")


def create_story_db():

    # CREATE STORY DB -----------------------------------------------------------------------------
    db_string = "postgresql://python:example@localhost:5433/story_db"
    engine = create_engine(db_string)


    # Create database if it does not exist.
    if database_exists(engine.url):
        print("StoryDB already exists")
        return

    create_database(engine.url)
    print("StoryDB created")


create_user_db()
create_story_db()