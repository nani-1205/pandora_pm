# config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env')) # Load .env file

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    WTF_CSRF_ENABLED = True

    # Remove static MONGODB_SETTINGS or set a default non-functional one
    # MONGODB_SETTINGS will be set dynamically in create_app after setup
    MONGODB_SETTINGS = {}

    # Optional: Add other configurations here