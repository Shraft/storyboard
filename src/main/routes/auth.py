import datetime

from flask import Flask, render_template, request, jsonify, make_response, redirect
import requests
from flask_restful import Resource
from flask_login import UserMixin
import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, create_refresh_token,
    get_jwt_identity, get_jwt, unset_jwt_cookies, unset_access_cookies, unset_refresh_cookies
)


def create_app():
    template_dir = os.path.abspath('../templates')

    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.config['SECRET_KEY'] = 'b14e74a8-635d-47e6-be96-45c4c99aed89'
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blacklist.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
    app.config['JWT_REFRESH_COOKIE_PATH'] = '/refresh'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False
    app.config['JWT_SECRET_KEY'] = 'b14e74a8-635d-47e6-be96-45c4c99aed89'
    return app

app = create_app()
jwtManager = JWTManager(app)

db = SQLAlchemy()
db.init_app(app)


HOST_IP = "localhost"


class TokenBlocklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False)

with app.app_context():
    db.create_all()


@jwtManager.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    jti = jwt_payload["jti"]
    token = db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()

    return token is not None


@jwtManager.unauthorized_loader
def missing_token_callback(callback):
    return make_response(redirect('/login'))


class User(UserMixin):
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username
    
    def get_id(self):
           return (self.user_id)


def load_user(user_id):
    response = requests.get(f"http://{HOST_IP}:5001/api/user/{user_id}") 
    if response.status_code == 404:
        print("\n\n Da muss wohl jemand seinen Chache und die Cokies mal löschen  \n\n")
        return None

    return User(response.json()["user_id"], response.json()["username"])


class Register(Resource):

    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('registration.html'),200,headers)

    def post(self):
        # get params from html form
        payload = {'username': request.form["username"],
                    'email': request.form["email"],
                    'password': request.form["password"]}

        # call user_management to create user
        response = requests.post(f"http://{HOST_IP}:5001/api/users", json=payload)

        # check html codes
        if response.status_code == 400:
            if response.json()['error_code'] == 1:
                error = 'Bitte alle Felder ausfüllen.'
            elif response.json()['error_code'] == 2:
                error = 'Nutzername und Email existieren bereits.'
            elif response.json()['error_code'] == 3:
                error = 'Die Email existiert bereits.'
            elif response.json()['error_code'] == 4:
                error = 'Der Nutzername existiert bereits.'
            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('registration.html', error=error), 200, headers)

        if response.status_code == 200:
            print("Operation Succesfull")
            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('login.html'), 200, headers)
        else:
            print("ErrorCode by user_management: " + str(response.status_code))
            return render_template('registration.html')

class Login(Resource):

    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('login.html'),200,headers)


    def post(self):
        if request.form["username"] == "" or request.form["password"] == "":
            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('login.html', error = "Du musst schon was eingeben"),200,headers)

        payload = {"username": request.form["username"],
                    "password": request.form["password"]}


        response = requests.post(f"http://{HOST_IP}:5001/api/user/login", data=payload)         # CHANGE

        if response.status_code != 200:
            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('login.html', error = response.json()["error"]),200,headers)
        identity = {
            'user_id': response.json()['user_id'],
            'username': response.json()['username']
        }
        resp = make_response(redirect('/get_stories'))
        resp = create_and_set_jwt_tokens(identity, resp)

        return resp


class Logout(Resource):
    @jwt_required()
    def get(self):
        response = make_response(redirect('/login'))
        delete_jwt_tokens_and_cookies(response)
        return response


# Helper methods

def delete_jwt_tokens_and_cookies(response):
    response.delete_cookie("access_token_cookie")
    response.delete_cookie("refresh_token_cookie")
    jti = get_jwt()["jti"]
    now = datetime.now(timezone.utc)
    db.session.add(TokenBlocklist(jti=jti, created_at=now))
    db.session.commit()
    unset_jwt_cookies(response)
    unset_access_cookies(response)
    unset_refresh_cookies(response)
    return response


def create_and_set_jwt_tokens(identity, response):
    access_token = create_access_token(identity=identity)
    refresh_token = create_refresh_token(identity=identity)
    response.set_cookie('access_token_cookie', access_token, max_age=1800, path=app.config['JWT_ACCESS_COOKIE_PATH'])
    response.set_cookie('refresh_token_cookie', refresh_token, expires=datetime.now() + timedelta(seconds=5), path=app.config['JWT_REFRESH_COOKIE_PATH'])
    return response

def refresh_access_token(identity, response):
    response = delete_jwt_tokens_and_cookies(response)
    new_access_token = create_access_token(identity=identity)
    response.set_cookie('access_token_cookie', new_access_token, max_age=1800,
                        path=app.config['JWT_ACCESS_COOKIE_PATH'])
    return response