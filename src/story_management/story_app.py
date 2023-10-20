from flask import Flask, jsonify, request, abort, make_response, render_template
from sqlalchemy import create_engine, Column, func, desc
from sqlalchemy.orm import sessionmaker
from create_db_tables import *
from sqlalchemy_utils import drop_database
from datetime import datetime
from flask_restful import Api, Resource
from sqlalchemy.exc import IntegrityError
import requests
import os


HOST_IP = "localhost"



# init flask
app = Flask(__name__)
app.debug = True



# init db stuff
db_string = f"postgresql://python:example@{HOST_IP}:5433/story_db"
engine = create_engine(db_string)
engine.connect()
Session = sessionmaker()
my_session = Session(bind=engine)



class Drop_Table(Resource):
    def get(self):
        drop_database(engine.url)
        print("### Database droped ###")



class Manage_Story(Resource):


    def create_tagged_persons(self, sid, tagged_persons_list):
        # get uids
        response = requests.get(f"http://{HOST_IP}:5001/api/tagged_users/" + str(tagged_persons_list))
        tagged_user_ids = response.json()

        # delete current references
        my_session.query(Story_persons).filter(Story_persons.story_id == sid).delete()
        my_session.commit()

        # add new references
        for uid in tagged_user_ids:
            uid_sid_relation = Story_persons(story_id = sid, user_id = uid)
            my_session.add(uid_sid_relation)
        my_session.commit()





    def do_users_notifications(self, sid, tagged_persons_list, creator_id):
        response = requests.get(f"http://{HOST_IP}:5001/api/tagged_users/" + str(tagged_persons_list))
        tagged_user_ids = response.json()

        #create notification
        for uid in tagged_user_ids:
            if uid == int(creator_id):
                continue

            payload = {"story_id" : sid, "user_id" : uid}
            response = requests.post(f"http://{HOST_IP}:5003/api/notifications/new_story", json=payload)
            print(f"Benachrichtigung erstellt [type: created, uid: {str(uid)}")

    def update_tagged_persons(self, sid, tagged_persons_list):
        # get uids
        response = requests.get(f"http://{HOST_IP}:5001/api/tagged_users/" + str(tagged_persons_list))
        tagged_user_ids = response.json()

        temp_ids = my_session.query(Story_persons).filter(Story_persons.story_id == sid).all()

        current_user_ids = []
        for uid in temp_ids:
            current_user_ids.append(uid.user_id)

        # notifications
        new_users = list(set(tagged_user_ids) - set(current_user_ids))
        for uid in new_users:
            payload = {"story_id" : sid, "user_id" : int(uid)}
            response = requests.post(f"http://{HOST_IP}:5003/api/notifications/tagged", json=payload)
            print(f"Benachrichtigung erstellt [type: tagged, uid: {str(uid)}")

        # delete current references
        my_session.query(Story_persons).filter(Story_persons.story_id == sid).delete()
        my_session.commit()

        # add new references
        for uid in tagged_user_ids:
            uid_sid_relation = Story_persons(story_id = sid, user_id = uid)
            my_session.add(uid_sid_relation)
        my_session.commit()


    def create_tag_table(self, tags, sid):
        tag_list = list(filter(None, tags.split("#")))

        for tag in tag_list:
            # check if tag exists
            if my_session.query(Tags).filter(Tags.name == tag).first() is None:
                db_tag = Tags(name = tag)    
                my_session.add(db_tag)
                my_session.commit()
                print(f'tag added {tag}')

            # get tag id
            tid = my_session.query(Tags).filter(Tags.name == tag).first().tag_id
            # referenz eintragen
            story_tag_ref = Story_tags(story_id = sid, tag_id = tid)
            my_session.add(story_tag_ref)
            my_session.commit()


    def post(self):
        # check if title exists
        story = my_session.query(Story).filter(Story.title == request.form["title"]).first()
        if story != None:
            headers = {'Content-Type': 'text/html'}
            return make_response(jsonify({"error" : "story exists"}),200,headers)

        story_is_public = True if request.form["public"] == "true" else False

        # create story
        story = Story(title = request.form["title"], text = request.form["text"], creator=request.form["creator_id"], 
            story_date=request.form["story_date"], creation_date = request.form["creation_date"],
            last_edited_date = request.form["last_edited_date"], public = story_is_public)
        my_session.add(story)

        # get story id
        sid = my_session.query(Story).filter(Story.title == request.form["title"]).first().story_id

        # speichere personen
        self.create_tagged_persons(sid, request.form["persons"])
        # create notifications
        self.do_users_notifications(sid, request.form["persons"], request.form["creator_id"])

        # speichere tags in extra tabelle
        self.create_tag_table(request.form["tags"], sid)


        # return story id of created story
        headers = {'Content-Type': 'text/html'}
        return make_response(jsonify({"story_id" : story.story_id}),200,headers)


    def delete(self):
        sid = request.form["story_id"]
        
        print(sid)
        
        story = my_session.query(Story).filter(Story.story_id == sid).delete()
        tags = my_session.query(Story_tags).filter(Story_tags.story_id == sid).delete()
        users = my_session.query(Story_persons).filter(Story_persons.story_id == sid).delete()
        my_session.commit()

        return 200

    
    def get(self):
        sid = request.form["story_id"]

        users = my_session.query(Story_persons).filter(Story_persons.story_id == sid).all()
        user_ids = []
        for user in users:
            user_ids.append(user.user_id)
        
        usernames = requests.post(f"http://{HOST_IP}:5001/api/tagged_users", json={"uid_list" : user_ids})
        usernames = usernames.json()

        users_string = ""
        for user in usernames:
            users_string += f'@{user}'

        tag_string = ""
        tags = my_session.query(Story_tags).filter(Story_tags.story_id == sid).all()
        for tag in tags:
            tid = tag.tag_id
            tag_name = my_session.query(Tags).filter(Tags.tag_id == tid).first().name
            tag_string += f'#{str(tag_name)}'

        story = my_session.query(Story).filter(Story.story_id == sid).first()

        # get picture infos
        pictures = my_session.query(Story_pictures).filter(Story_pictures.story_id == sid).all()
        picture_list = []
        for picture in pictures:
            picture_list.append(picture.path)

        # get username
        username = requests.post(f"http://{HOST_IP}:5001/api/tagged_users", json={"uid_list" : [story.creator]}).json()[0]

        # get type (user is creator, is tagged, or its public)
        if request.form["username"] == username:
            story_type = "created"
        elif request.form["username"] in usernames:
            story_type = "tagged"
        else:
            story_type = "public"

        storyObject = {
                    'type': story_type,
                    'creator': username,
                    'text': "" if story.text is None else story.text,
                    'title': "" if story.title is None else story.title ,                       # Warum?
                    'story_date': story.story_date.strftime("%Y-%m-%d"),
                    'last_edited_date': story.story_date.strftime("%Y-%m-%d"),
                    'creation_date': story.story_date.strftime("%Y-%m-%d"),
                    'story_id': "" if story.story_id is None else story.story_id,
                    'tags' : tag_string,
                    'persons' : users_string,
                    'pictures' : picture_list,
                    'picture_count': len(picture_list),
                    'public' : "checked" if story.public == True else ""}

        headers = {'Content-Type': 'text/html'}
        return make_response(jsonify(storyObject),200,headers)


    def put(self):

        my_session.query(Story).filter(Story.story_id == request.form["story_id"]).update(
            {
                Story.title: request.form["title"],
                Story.text: request.form["text"],
                Story.last_edited_date: request.form["last_edited_date"],
                Story.story_date: request.form["story_date"],
                Story.public: True if request.form["public"] == "true" else False
            }
        )
        my_session.query(Story_tags).filter(Story_tags.story_id == request.form["story_id"]).delete()
        my_session.commit()
        self.create_tag_table(request.form["tags"], request.form["story_id"])

        self.update_tagged_persons(request.form["story_id"], request.form["persons"])

        headers = {'Content-Type': 'text/html'}
        return make_response("done",200,headers)


class Get_Stories(Resource):


    def create_story_object(self, story):
        story_date = story.story_date.strftime("%d.%m.%Y")
        last_edited_date = story.last_edited_date.strftime("%d.%m.%Y")
        creation_date = story.creation_date.strftime("%d.%m.%Y")

        # get tags
        tag_string = ""
        tags = my_session.query(Story_tags).filter(Story_tags.story_id == story.story_id).all()
        for tag in tags:
            tagname = my_session.query(Tags).filter(Tags.tag_id == tag.tag_id).first().name
            tag_string += f'#{str(tagname)}'

        # get users
        persons = my_session.query(Story_persons).filter(Story_persons.story_id == story.story_id).all()
        user_ids = []
        for user in persons:
            user_ids.append(user.user_id)
        usernames = requests.post(f"http://{HOST_IP}:5001/api/tagged_users", json={"uid_list" : user_ids})
        usernames = usernames.json()

        users_string = ""
        for user in usernames:
            users_string += f'@{user}'

        
        # get username
        username = requests.post(f"http://{HOST_IP}:5001/api/tagged_users", json={"uid_list" : [story.creator]}).json()[0]


        storyObject = {
                'creator': username,
                'text': story.text,
                'title': story.title,
                'story_date': story_date,
                'last_edited_date': last_edited_date,
                'creation_date': creation_date,
                'story_id': story.story_id,
                'tags' : tag_string,
                'persons': users_string
        }
        return storyObject


    def get(self):

        uid = request.form["user_id"]

        story_count = {}

        # get all created stories
        created_stories_list = []
        anti_doubling_list = []
        created_stories = my_session.query(Story).filter(Story.creator == uid).order_by(desc(Story.story_date)).all()
        counter = 0
        for story in created_stories:
            storyObject = self.create_story_object(story)
            created_stories_list.append(storyObject)
            anti_doubling_list.append(story.story_id)
            counter += 1
        story_count["created_stories"] = counter

        # get all tagged stories
        tagged_stories_list = []
        user_is_tagged_stories = my_session.query(Story_persons).filter(Story_persons.user_id == uid).all()
        counter = 0
        for story_id in user_is_tagged_stories:  
            story = my_session.query(Story).filter(Story.story_id == story_id.story_id).first()
            if story_id.story_id in anti_doubling_list:
                continue

            storyObject = self.create_story_object(story)
            tagged_stories_list.append(storyObject)
            counter += 1
        story_count["tagged_stories"] = counter


        # get all public stories
        public_stories_list = []
        public_stories = my_session.query(Story).filter(Story.public == True).order_by(desc(Story.story_date)).all()
        counter = 0
        for story in public_stories:
            if story.story_id in anti_doubling_list:
                continue
            storyObject = self.create_story_object(story)
            public_stories_list.append(storyObject)
            counter += 1
        story_count["public_stories"] = counter

        headers = {'Content-Type': 'text/html'}
        payload = {"tagged_stories" : tagged_stories_list,
                    "created_stories" : created_stories_list,
                    "public_stories" : public_stories_list,
                    "story_count" : story_count}
        return make_response(jsonify(payload),200,headers)



class Manage_Pictures(Resource):

    def post(self):
        try:
            highest_pic = my_session.query(func.max(Story_pictures.picture_id)).first()[0]
        except:
            highest_pic = 0

        if highest_pic is None:
            highest_pic = 0

        headers = {'Content-Type': 'text/html'}
        return make_response(jsonify({'start_index' : highest_pic+1 }),200,headers)

    def put(self):
        data = request.get_json(force=True)

        sid = data["sid"]
        img_start_index = int(data["img_start_index"])
        img_count = int(data["img_count"])
        filename = data["filename"]
        relative_path = data["relative_path"]


        file_type_list = data["file_type_list"]
        print(file_type_list)

        ftl_count = 0
        for i in range(img_start_index, img_start_index + img_count, 1):
            path = relative_path + "/" + filename + str(i) + file_type_list[ftl_count]
            Picture = Story_pictures(story_id = sid, picture_id = i, path = path)
            my_session.add(Picture)
            ftl_count +=1
        my_session.commit()

        headers = {'Content-Type': 'text/html'}
        return make_response(jsonify("positive"),200,headers)


    def delete(self):
        sid = request.form["story_id"]
        picpath = request.form["picpath"]

        # delete from db
        my_session.query(Story_pictures).filter(Story_pictures.path == picpath).delete()
        my_session.commit()

        headers = {'Content-Type': 'text/html'}
        return make_response(jsonify("positive"),200,headers)





# Adds prefix '/api' to routes
api = Api(app, prefix='/api')


# All the user api routes
api.add_resource(Manage_Story, '/story')
api.add_resource(Get_Stories, '/stories')
api.add_resource(Manage_Pictures, '/story_pictures')

api.add_resource(Drop_Table, '/drop_table')

app.run(host="0.0.0.0", port=5002)




