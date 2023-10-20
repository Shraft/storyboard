import logging
from flask import request
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, jsonify, make_response
from flask_login import UserMixin
from sqlalchemy_utils import drop_database
import os


HOST_IP = "localhost"



logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger()

db = SQLAlchemy()
app = Flask(__name__)


db_string = f"postgresql://python:example@{HOST_IP}:5432/user_db"
engine = create_engine(db_string)

if not database_exists(engine.url):
    create_database(engine.url)
    print("UserDB created")
else:
    print("UserDB already exists")

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://python:example@{HOST_IP}:5432/user_db"
db.init_app(app)


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password


with app.app_context():
    db.create_all()



class Drop_Table(Resource):
    def get(self):
        drop_database(engine.url)
        print("### Database droped ###")

class UserApi(Resource):

    # returns user for given id
    def get(self, user_id):
        user = User.query.filter_by(user_id=user_id).first_or_404()
        print(user)
        return user_as_json(user), 200

    # updates user for given id
    def put(self, update_type, user_id):

        # update user data (username, email)
        if update_type == 'data':
            data = request.get_json(force=True)
            user = User.query.filter_by(user_id=user_id).first()
            if user is not None:
                user.username = data['username'].lower()
                user.email = data['email'].lower()
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    return 'Integrity Error.', 409
                return user_as_json(user), 200
            else:
                return 'User id does not exist.', 404
        # update user password
        elif update_type == 'password':
            data = request.get_json(force=True)
            user = User.query.filter_by(user_id=user_id).first()
            if user is not None:
                # check if current password is correct
                if not check_password_hash(str(user.password), data['current_password']):
                    return "Current password incorrect.", 400
                user.password = generate_password_hash(data['new_password'], method='sha256')
                db.session.commit()
                return user_as_json(user), 200
            else:
                return 'User id does not exist.', 404
        else:
            return 'Invalid update type in route.', 404


    # deletes user for given id
    def delete(self, user_id):
        User.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return 'User was deleted.', 200


class UsersApi(Resource):

    # returns all users
    def get(self):
        users = User.query.all()
        users_json = list()
        for user in users:
            users_json.append(user_as_json(user))
        return users_json, 200

    # creates a new user
    def post(self):
        data = request.get_json(force=True)

        username = data['username']
        email = data['email']
        password = data['password']

        # check if username, email and password are none or empty
        if username is None or username == '' or email is None or email == '' or password is None or password == '':
            return {'error_code': 1}, 400

        # make username and email all lowercase
        username = username.lower()
        email = email.lower()

        # check if username or email already exist
        existing_username = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()
        if existing_username and existing_email:
            return {'error_code': 2}, 400
        elif existing_email:
            return {'error_code': 3}, 400
        elif existing_username:
            return {'error_code': 4}, 400

        # hash password
        pw_hashed = generate_password_hash(password, method='sha256')

        # try add user to db
        user = User(username, email, pw_hashed)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return 'Integrity Error.', 409
        return user_as_json(user), 200


class UserLogin(Resource):
    def post(self):

        user = db.session.query(User).filter(User.username == request.form["username"]).first()

        if (user == None) or not check_password_hash(str(user.password), str(request.form["password"])):
                headers = {'Content-Type': 'text/html'}
                return make_response(jsonify({"error" : "Zugangsdaten stimmen nicht"}),400,headers)
                    
        
        user = db.session.query(User).filter(User.username == request.form["username"]).first()

        payload = {"user_id" : user.user_id,
                    "username" : user.username}

        headers = {'Content-Type': 'text/html'}
        return make_response(jsonify(payload), 200, headers)


class TaggedUsers(Resource):
    # get usernames by uid list
    def post(self):
        message = request.get_json(force=True)
        uid_list = message["uid_list"]
        usernames = []
        for uid in uid_list:
            usernames.append(db.session.query(User).filter(User.user_id == uid).first().username)
        return usernames

    # get uids by username string
    def get(self, tagged_users=None):
        # e.g. tagged_users = “@Nina@Nilss@Rica”
        # split tagged user string into usernames
        if tagged_users is None:
            return []
        tagged_users_list = tagged_users.split("@")
        # filter out existing users and return list of tagged user ids
        tagged_user_ids = []
        for user in tagged_users_list:
            user = User.query.filter_by(username=user).first()
            if user is not None:
                tagged_user_ids.append(user.user_id)
        return tagged_user_ids


# Adds prefix '/api' to routes
api = Api(app, prefix='/api')

# All the user api routes
api.add_resource(UserApi, '/user/<string:user_id>', '/user/<string:update_type>/<string:user_id>')
api.add_resource(UsersApi, '/users')
api.add_resource(UserLogin, '/user/login')
api.add_resource(TaggedUsers, '/tagged_users/<string:tagged_users>', '/tagged_users/', '/tagged_users')

api.add_resource(Drop_Table, '/drop_table')


#   HELPER FUNCTIONS

#   returns a user object as json
def user_as_json(user):
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "password": user.password
    }


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)

