# pandora_pm/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '..', '.env') # Path is one level up from app/
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
     # Try loading from current directory if .env is beside config.py (less common setup)
     load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/pandora_pm_dev_db'
    DEBUG = False
    TESTING = False
    # Add other default settings if needed

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    MONGO_URI = os.environ.get('MONGO_URI_DEV') or Config.MONGO_URI # Allow separate dev DB

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    MONGO_URI = os.environ.get('MONGO_URI_TEST') or 'mongodb://localhost:27017/pandora_pm_test_db'
    WTF_CSRF_ENABLED = False # Disable CSRF for tests often

class ProductionConfig(Config):
    """Production configuration."""
    MONGO_URI = os.environ.get('MONGO_URI')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not MONGO_URI or not SECRET_KEY:
        # In a real app, you might log this error instead of raising immediately
        # raise ValueError("No MONGO_URI or SECRET_KEY set for production environment variables")
        print("WARNING: No MONGO_URI or SECRET_KEY set for production via environment variables!") # Temporary warning

# Dictionary to easily select config based on environment variable
config_by_name = dict(
    development=DevelopmentConfig,
    testing=TestingConfig,
    production=ProductionConfig,
    default=DevelopmentConfig
)

def get_config_name():
    return os.getenv('FLASK_ENV', 'default')

def get_config():
    """Returns the appropriate config class based on FLASK_ENV."""
    config_name = get_config_name()
    return config_by_name.get(config_name, DevelopmentConfig)