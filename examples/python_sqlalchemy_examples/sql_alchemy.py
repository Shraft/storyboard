from sqlalchemy import create_engine, Column
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import psycopg2
from init_db import User, Session, engine
import time


my_session = Session(bind=engine)
try:

    # add user
    user = User(email='markus@gmx.de', name='Markus', password='123')
    my_session.add(user)
    my_session.commit()
    print("added user")
    time.sleep(5)


    # get user
    person = my_session.query(User).all()   # get all entries
    person = my_session.query(User).filter(User.name == "Markus").first()   # get first of all

    if person == None:
        print("no entries")
    else:
        print("get user: " + person.email)

    time.sleep(5)


    # update informations
    my_session.query(User).filter(User.name == "Markus").update(
        {
            User.name: "Marxiander"
        }
    )

    my_session.commit()
    print("updated user")
    time.sleep(5)


    # remove person
    person = my_session.query(User).get(1)      # get 1 entry 
    my_session.delete(person)
    my_session.commit()
    print("removed user")



except:
    print("error")

my_session.close()