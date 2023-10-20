from flask import render_template, request, redirect, make_response, send_file, url_for
import requests
import os
from flask_restful import Resource
import shutil
from datetime import datetime
from flask_jwt_extended import (
    jwt_required, get_jwt_identity
)

from .auth import delete_jwt_tokens_and_cookies, create_and_set_jwt_tokens, refresh_access_token

HOST_IP = "localhost"


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    return "." + filename.rsplit('.', 1)[1].lower()



class Drop_Tables(Resource):
    @jwt_required()
    def get(self):
        requests.get(f"http://{HOST_IP}:5001/api/drop_table")
        requests.get(f"http://{HOST_IP}:5002/api/drop_table")
        requests.get(f"http://{HOST_IP}:5003/api/drop_table")
        print("### All Databases deletet ###")

        # delete images
        TARGET_PATH = os.getcwd() + '/src/main/static/res/'
        try:
            shutil.rmtree(TARGET_PATH)
            print("### Bilder und Dateien wurden entfernt ###")
        except FileNotFoundError:
            print("### Es gab keine Dateien zu entfernen ###")

        return redirect("/get_stories")

class Index(Resource):
    @jwt_required()
    def get(self):
        return redirect("/get_stories")


class Images(Resource):
    # get all images as .zip
    @jwt_required()
    def get(self, sid , title):
        filename = title.replace(" ","_") + "_bilder"
        TARGET_PATH = os.getcwd() + '/src/main/static/' + "res/sid" + sid + "/"
        ARCHIVE_PATH = os.getcwd() + '/src/main/static/' + "res/"
        shutil.make_archive(ARCHIVE_PATH + filename, 'zip', TARGET_PATH)
        print(f"Bilder von story_id: {sid} wurden verpackt")

        return send_file(os.path.join(ARCHIVE_PATH, filename + ".zip"), as_attachment=True)

    # delete single image
    @jwt_required()
    def post(self):

        payload = {'picpath': request.form["picpath"],
                    'story_id': request.form["sid"]}

        response = requests.delete(f"http://{HOST_IP}:5002/api/story_pictures", data=payload) 

        if response.status_code == 200:
            print("Story geholt")
        else:
            print("ErrorCode by story_management: " + str(response.status_code))

        # delete from filesystem
        file_path = os.getcwd() + '/src/main/static/' + request.form["picpath"]
        os.remove(file_path)


        return redirect(f"/edit_story/{request.form['sid']}/{request.form['title']}")



class Show_Story(Resource):
    @jwt_required()
    def get(self,sid):
    
        response = requests.get(f"http://{HOST_IP}:5002/api/story", data={"story_id" : sid, "username": str(get_jwt_identity()['username'])})

        if response.status_code == 200:
            print("Story geholt")
        else:
            print("ErrorCode by user_management: " + str(response.status_code))

        print(response.json())
        

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('story.html',story = response.json()),200,headers)



class Create_Story(Resource):

    def create_individual_response_params(self, error, story_date):
        empty_story = {'text': "",'title' : "",'story_date' : story_date, 'persons': str("@" + get_jwt_identity()['username']), 'error' : error, 'public' : "", "picture_count" : 0}
        return empty_story

    
    def save_images(self, request, sid):
        # get start index
        response = requests.post(f"http://{HOST_IP}:5002/api/story_pictures", data={'sid' : sid})
        image_start_index = int(response.json()['start_index'])

        # get images
        uploaded_files = request.files.getlist("file[]")
        # save images
        img_counter = 0
        file_type_list = []
        filename = ""
        relative_path = ""
        for file in uploaded_files:               
            if file and allowed_file(file.filename):   
                file_type = get_file_type(file.filename) 
                file_type_list.append(file_type)
                filename = "sid" + sid + '_'
                fully_filename = filename + str(img_counter + image_start_index) + file_type
                relative_path = "res/sid" + sid
                TARGET_PATH = os.getcwd() + '/src/main/static/' + relative_path

                print(TARGET_PATH)

                if not os.path.exists(TARGET_PATH):
                    os.makedirs(TARGET_PATH)

                file.save(os.path.join(TARGET_PATH, fully_filename))
                img_counter += 1

        payload = {'sid' : sid,
                    'img_start_index' : image_start_index,
                    'img_count' : img_counter,
                    'filename' : "" if filename is None else filename,
                    'file_type_list': file_type_list,
                    'relative_path' : relative_path}
        response = requests.put(f"http://{HOST_IP}:5002/api/story_pictures", json=payload)

    @jwt_required()
    def get(self):
        headers = {'Content-Type': 'text/html'}
        empty_story = self.create_individual_response_params("", datetime.now().strftime("%Y-%m-%d"))
        return make_response(render_template('create_story.html', story = empty_story),200,headers)

    @jwt_required()
    def post(self):
        
        # if new story
        if request.form["sid"] == "":

            print(str(False if request.form.get("public") is None else True))

            payload = {'creator' : str(get_jwt_identity()['username']),
                    'creator_id' : str(get_jwt_identity()['user_id']),
                    'title' : request.form["title"] ,
                    'text' : request.form["text"],
                    'persons' : request.form["persons"],
                    'tags' : request.form["tags"],
                    'story_date' : request.form["story_date"],
                    'creation_date': datetime.now().strftime("%Y-%m-%d"),
                    'last_edited_date': datetime.now().strftime("%Y-%m-%d"),
                    'public' : "false" if request.form.get("public") is None else "true"}

            response = requests.post(f"http://{HOST_IP}:5002/api/story", data=payload)    

            # check html codes
            if response.status_code == 200:
                print("Operation Succesfull")
            else:
                print("ErrorCode by story_management: " + response.json()["error"])
                empty_story = self.create_individual_response_params(response.json()["error"])
                headers = {'Content-Type': 'text/html'}
                return make_response(render_template('create_story.html', story = empty_story),200,headers)
                

            story_id = str(response.json()['story_id'])
            self.save_images(request, story_id)

            return redirect(f"/show_story/{response.json()['story_id']}")

        # if story exists (its an update of the story)
        else:
            print(request.form.get("public"))

            sid = request.form["sid"]
            payload = {'title' : request.form["title"] ,
                    'text' : request.form["text"],
                    'persons' : request.form["persons"],
                    'tags' : request.form["tags"],
                    'story_date' : request.form["story_date"],
                    'story_id': request.form["sid"],
                    'last_edited_date': datetime.now().strftime("%Y-%m-%d"),
                    'public' : "false" if request.form.get("public") is None else "true"}

            response = requests.put(f"http://{HOST_IP}:5002/api/story", data=payload)  
            
            self.save_images(request, sid)

            return redirect(f"/show_story/{request.form['sid']}")
        
        



class Edit_Story(Resource):
    @jwt_required()
    def get(self,sid, title):
        response = requests.get(f"http://{HOST_IP}:5002/api/story", data={"story_id" : sid, "username": str(get_jwt_identity()['username'])})

        if response.status_code == 200:
            print("Story geholt")
        else:
            print("ErrorCode by user_management: " + str(response.status_code))

        print(response.json())
        

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('create_story.html',story = response.json()), 200,headers)



class Delete_Story(Resource):
    @jwt_required()
    def post(self):
        print("##################################")
        print(request.form["del_sid"])

        payload = {"story_id" : request.form["del_sid"]}
        response = requests.delete(f"http://{HOST_IP}:5002/api/story", data=payload)
        # check html codes
        if response.status_code == 200:
            print("Story entfernt")
        else:
            print("ErrorCode by user_management: " + str(response.status_code))

        # delete images
        TARGET_PATH = os.getcwd() + '/src/main/static/' + "res/sid" + request.form["del_sid"] + "/"
        try:
            shutil.rmtree(TARGET_PATH)
            print("Bilder und Dateien wurden entfernt")
        except FileNotFoundError:
            print("Es gab keine Dateien zu entfernen")
        

        return redirect('/get_stories')



class Get_Stories(Resource):
    @jwt_required()
    def get(self):
        response = requests.get(f"http://{HOST_IP}:5002/api/stories", data={'user_id' : str(get_jwt_identity()['user_id'])})

        # check html codes
        if response.status_code == 200:
            print("Operation Succesfull")
        else:
            print("ErrorCode by user_management: " + str(response.status_code))

        notifications = requests.get(f"http://{HOST_IP}:5003/api/user_notifications/{str(get_jwt_identity()['user_id'])}")
        notifications_count = len(notifications.json())

        print(response.json())
        created_stories = response.json()["created_stories"]
        tagged_stories = response.json()["tagged_stories"]
        public_stories = response.json()["public_stories"]
        story_count = response.json()["story_count"]

        headers = {'Content-Type': 'text/html'}
        resp = make_response(render_template(
            'stories.html',
            tagged_stories = tagged_stories,
            created_stories = created_stories,
            public_stories = public_stories,
            story_count = story_count,
            notifications_count = notifications_count
            ),200,headers)
        resp = refresh_access_token(get_jwt_identity(), resp)
        return resp

class User(Resource):
    @jwt_required()
    def get(self):
        # get user data for current user
        response = requests.get(f"http://{HOST_IP}:5001/api/user/" + str(get_jwt_identity()['user_id']))

        if response.status_code == 200:
            print("GET USER SUCCESSFUL")
        else:
            print("ErrorCode by user_management: " + str(response.status_code))

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('profile.html', user=response.json()), 200, headers)

    @jwt_required()
    def post(self, update_type):

        # update username and email
        if update_type == 'data':
            # check if form fields are empty
            if request.form["username"] == "" or request.form["email"] == "":
                return reload_profile("Bitte Felder ausfüllen.", None)
            payload = {
                'username': request.form["username"],
                'email': request.form["email"]
            }
            update_type = 'data'

        # update password
        elif update_type == 'password':
            # check if form fields are empty
            if request.form["current-password"] == "" or request.form["new-password"] == "":
                return reload_profile(None, "Bitte Felder ausfüllen.")
            payload = {
                'current_password': request.form["current-password"],
                'new_password': request.form["new-password"]
            }
            update_type = 'password'



        response = requests.put(f"http://{HOST_IP}:5001/api/user/" + update_type + "/" + str(get_jwt_identity()['user_id']),
                                json=payload)
        if response.status_code == 200:
            print("Update User successful.")
            headers = {'Content-Type': 'text/html'}

            # delete old access tokens and create new tokens with new userdata
            user_data = response.json()

            resp = make_response(render_template('profile.html', user=response.json()), 200, headers)
            resp = delete_jwt_tokens_and_cookies(resp)

            # update access und refresh tokens after username change
            identity = {
                'user_id': user_data['user_id'],
                'username': user_data['username']
            }
            resp = create_and_set_jwt_tokens(identity, resp)
            return resp

        elif response.status_code == 400:
            return reload_profile(None, "Aktuelles Passwort inkorrekt.")
        elif response.status_code == 409:
            return reload_profile("Die Email oder der Nutzername existieren bereits.", None)
        else:
            print("ErrorCode by user_management: " + str(response.status_code))


class Notifications(Resource):
    @jwt_required()
    def get(self):
        # get notifications for current user
        response = requests.get(f"http://{HOST_IP}:5003/api/user_notifications/" + str(get_jwt_identity()['user_id']))

        if response.status_code == 200:
            print("GET Notifications SUCCESSFUL")
        else:
            print("ErrorCode by notification_management: " + str(response.status_code))

        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('notification.html', notifications=response.json()), 200, headers)


class Delete_Notifications(Resource):
    @jwt_required()
    def post(self):
        # delete all notifications of user at once
        response = requests.delete(f"http://{HOST_IP}:5003/api/user_notifications/" + str(get_jwt_identity()['user_id']))
        if response.status_code == 200:
            print("Delete user notifications successful.")
        else:
            print("ErrorCode by notification_management: " + str(response.status_code))

        response = requests.get(f"http://{HOST_IP}:5003/api/user_notifications/" + str(get_jwt_identity()['user_id']))
        headers = {'Content-Type': 'text/html'}
        return redirect(url_for("index"))


class Delete_Notification(Resource):
    @jwt_required()
    def post(self):
        # delete a user notification
        response = requests.delete(f"http://{HOST_IP}:5003/api/notification/" + request.form["notification_id"])
        if response.status_code == 200:
            print("Delete user notification successful.")
        else:
            print("ErrorCode by notification_management: " + str(response.status_code))

        response = requests.get(f"http://{HOST_IP}:5003/api/user_notifications/" + str(get_jwt_identity()['user_id']))
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('notification.html', notifications=response.json()), 200, headers)


# HELPER METHODS

def reload_profile(data_error, password_error):
    headers = {'Content-Type': 'text/html'}
    response = requests.get(f"http://{HOST_IP}:5001/api/user/" + str(get_jwt_identity()['user_id']))
    if data_error is not None:
        return make_response(
            render_template('profile.html', user=response.json(), data_error=data_error),
            200, headers)
    elif password_error is not None:
        return make_response(
            render_template('profile.html', user=response.json(), password_error=password_error),
            200, headers)
