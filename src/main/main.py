from flask import Blueprint, render_template
from routes import *
from flask_restful import Api
from routes.auth import Register, Login, Logout
from routes.basic import Create_Story, Delete_Story, Index, Get_Stories, Edit_Story, User, Show_Story, Drop_Tables, Images, Notifications, Delete_Notifications, Delete_Notification


from routes.auth import app
api = Api(app)



# All user api routes
api.add_resource(Register, '/register')
api.add_resource(Login, '/login')
api.add_resource(Logout, '/logout')
api.add_resource(User, '/user', '/user/<string:update_type>')

# All story routes
api.add_resource(Index, '/')
api.add_resource(Images, '/images/<string:sid>/<string:title>', '/images')
api.add_resource(Create_Story, '/create_story')
api.add_resource(Delete_Story, '/delete_story')
api.add_resource(Get_Stories, '/get_stories')
api.add_resource(Drop_Tables, '/drop_tables')
api.add_resource(Show_Story, '/show_story/<string:sid>')
api.add_resource(Edit_Story, '/edit_story/<string:sid>/<string:title>')

# All notification routes
api.add_resource(Notifications, '/notifications')
api.add_resource(Delete_Notifications, '/notifications/delete')
api.add_resource(Delete_Notification, '/notification/delete')


app.debug = True
app.run(host="0.0.0.0")