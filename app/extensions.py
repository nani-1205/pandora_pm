# pandora_pm/app/extensions.py
from flask_pymongo import PyMongo
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

mongo = PyMongo()
login_manager = LoginManager()
bcrypt = Bcrypt()

# Configure Flask-Login
login_manager.login_view = 'auth.login' # Blueprint 'auth', route 'login'
login_manager.login_message_category = 'info' # Bootstrap class for flash messages
login_manager.login_message = 'Eywa requires you to log in to access this area.'

# Tells Flask-Login how to load a user from the user ID stored in the session
@login_manager.user_loader
def load_user(user_id):
    """Loads user object for Flask-Login."""
    # Import here to avoid circular imports
    from .models import User
    return User.get_by_id(user_id)