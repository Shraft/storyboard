from sqlalchemy import create_engine, Column
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.sqltypes import String, Integer, DateTime, Boolean
from sqlalchemy_utils import database_exists, create_database
import psycopg2
import os


HOST_IP = "localhost" 



# CREATE STORY DB -----------------------------------------------------------------------------
db_string = f"postgresql://python:example@{HOST_IP}:5433/story_db"
engine = create_engine(db_string)


# Create database if it does not exist.
if not database_exists(engine.url):
    create_database(engine.url)

# connect and initiate
engine.connect()
base = declarative_base()
conn = engine.connect()
Session = sessionmaker()

class Story(base):
        __tablename__ = 'stories'
        story_id = Column(Integer, primary_key=True) 
        title = Column(String(100), unique=True)
        text = Column(String(4096))
        story_date = Column(DateTime)
        creator = Column(Integer)
        creation_date = Column(DateTime)
        last_edited_date = Column(DateTime)
        public = Column(Boolean)

class Story_tags(base):
    __tablename__ = 'story_tags'
    story_id = Column(Integer, primary_key=True) 
    tag_id = Column(Integer, primary_key=True)

class Story_persons(base):
    __tablename__ = 'story_persons'
    story_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, primary_key=True)

class Story_Comments(base):
    __tablename__ = 'story_comments'
    story_id = Column(Integer, primary_key=True)
    comment = Column(String(100))
    creator = Column(String(100))
    creation_date = Column(DateTime)

class Tags(base):
    __tablename__ = 'tags'
    tag_id = Column(Integer, primary_key=True) 
    name = Column(String(100), unique=True)

class Story_pictures(base):
    __tablename__ = 'story_pictures'
    story_id = Column(Integer, primary_key=True) 
    picture_id = Column(Integer, primary_key=True) 
    path = Column(String(120), unique=True)

base.metadata.create_all(conn)
print("StoryDB created")