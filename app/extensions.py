# pandora_pm/app/extensions.py
from flask_pymongo import PyMongo
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

mongo = PyMongo()
login_manager = LoginManager()
bcrypt = Bcrypt()

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.get_by_id(user_id)