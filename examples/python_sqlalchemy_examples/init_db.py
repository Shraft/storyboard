from sqlalchemy import create_engine, Column
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.sqltypes import String, Integer
from sqlalchemy_utils import database_exists, create_database
import psycopg2



db_string = "postgresql://python:example@localhost:5432/user_db"
engine = create_engine(db_string)


# Create database if it does not exist.
if not database_exists(engine.url):
    create_database(engine.url)

# connect and initiate
engine.connect()
base = declarative_base()
conn = engine.connect()
Session = sessionmaker()


class User(base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = Column(String(100), unique=True)
    password = Column(String(100))
    name = Column(String(1000))


base.metadata.create_all(conn)



