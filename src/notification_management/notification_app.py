import logging
from flask import request
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database, drop_database
from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from sqlalchemy_utils import drop_database
import os



HOST_IP = "localhost"


logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger()

db = SQLAlchemy()
app = Flask(__name__)


db_string = f"postgresql://python:example@{HOST_IP}:5434/notification_db"
engine = create_engine(db_string)

if not database_exists(engine.url):
    create_database(engine.url)
    print("NotificationDB created")
else:
    print("NotificationDB already exists")

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://python:example@{HOST_IP}:5434/notification_db"
db.init_app(app)



class Notification(db.Model):
    __tablename__ = 'notification'
    notification_id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String, nullable=False)

    def __init__(self, story_id, user_id, message):
        self.story_id = story_id
        self.user_id = user_id
        self.message = message


with app.app_context():
    db.create_all()


class DropTable(Resource):
    def get(self):
        drop_database(engine.url)
        print("### Database droped ###")

# Message types
class Message:
    NEW_STORY = "Eine neue Story wurde erstellt."
    TAGGED = "Du wurdest in einer Story getagged."


class NotificationsApi(Resource):

    # returns all notifications
    def get(self):
        notifications = Notification.query.all()
        notifications_json = list()
        for notification in notifications:
            notifications_json.append(notification_as_json(notification))
        return notifications_json, 200

    def post(self, message_type):
        data = request.get_json(force=True)

        story_id = data['story_id']
        user_id = data['user_id']

        if message_type == 'new_story':
            message = Message.NEW_STORY
        elif message_type == 'tagged':
            message = Message.TAGGED

        # add notification to db
        notification = Notification(story_id, user_id, message)
        db.session.add(notification)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return 'Integrity Error.', 409
        return notification_as_json(notification), 200


class NotificationApi(Resource):

    def get(self, notification_id):
        notification = Notification.query.filter_by(notification_id=notification_id).first_or_404()
        return notification_as_json(notification), 200

    def delete(self, notification_id):
        delete_notification(notification_id)
        return 'Notification was deleted.', 200


class UserNotificationsApi(Resource):
    # returns all notifications for a given user
    def get(self, user_id):
        return get_user_notifications(user_id), 200

    def delete(self, user_id):
        user_notifications = get_user_notifications(user_id)
        for notification in user_notifications:
            delete_notification(notification['notification_id'])
        return 'user notifications deleted', 200


# Adds prefix '/api' to routes
api = Api(app, prefix='/api')

# All the user api routes
api.add_resource(NotificationsApi, '/notifications', '/notifications/<string:message_type>')
api.add_resource(NotificationApi, '/notification/<string:notification_id>')
api.add_resource(UserNotificationsApi, '/user_notifications/<string:user_id>')

api.add_resource(DropTable, '/drop_table')


#   HELPER FUNCTIONS

#   returns a notification object as json
def notification_as_json(notification):
    return {
        "notification_id": notification.notification_id,
        "story_id": notification.story_id,
        "user_id": notification.user_id,
        "message": notification.message
    }


# returns all notifications of a specific user
def get_user_notifications(user_id):
    user_notifications = Notification.query.filter_by(user_id=user_id).all()
    user_notifications_json = []
    for notification in user_notifications:
        user_notifications_json.append(notification_as_json(notification))
    return user_notifications_json


def delete_notification(notification_id):
    Notification.query.filter_by(notification_id=notification_id).delete()
    db.session.commit()


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5003, debug=True)

