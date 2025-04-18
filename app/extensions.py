# app/extensions.py
"""Module to initialize Flask extensions."""

from flask_mongoengine import MongoEngine
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

db = MongoEngine()
login_manager = LoginManager()
bcrypt = Bcrypt()