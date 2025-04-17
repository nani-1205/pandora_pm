# pandora_pm/app/extensions.py
from flask_pymongo import PyMongo
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

mongo = PyMongo()
login_manager = LoginManager()
bcrypt = Bcrypt()

# Configure Flask-Login
login_manager.login_view = 'auth.login' # Blueprint 'auth', view function 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Please log in to access this page.'

# Moved user_loader here to be centrally managed by the extension setup
@login_manager.user_loader
def load_user(user_id):
    """Loads user object for Flask-Login."""
    # Import User model here to avoid circular imports during initialization
    from .models import User
    return User.get_by_id(user_id)