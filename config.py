# pandora_pm/config.py
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus # Required for encoding credentials

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
     load_dotenv(os.path.join(basedir, '.env'))


# --- Read individual MongoDB components from environment ---
MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
MONGO_PORT = os.environ.get('MONGO_PORT', '27017')
MONGO_USER = os.environ.get('MONGO_USER')
MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD')
MONGO_AUTH_DB = os.environ.get('MONGO_AUTH_DB') # Auth source
DB_NAME = os.environ.get('DB_NAME') or 'pandora_pm_db' # Default app DB name

# --- Construct MONGO_URI ---
mongo_uri = "mongodb://"
if MONGO_USER and MONGO_PASSWORD:
    # Encode BOTH username and password using quote_plus (as required by PyMongo)
    encoded_user = quote_plus(MONGO_USER)
    encoded_password = quote_plus(MONGO_PASSWORD)
    mongo_uri += f"{encoded_user}:{encoded_password}@"
mongo_uri += f"{MONGO_HOST}:{MONGO_PORT}/"
mongo_uri += f"{DB_NAME}"
if MONGO_USER and MONGO_AUTH_DB:
    mongo_uri += f"?authSource={MONGO_AUTH_DB}"
# print(f"Constructed MONGO_URI: {mongo_uri}") # For debugging if needed


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_default_secret_key_change_it'
    MONGO_URI = mongo_uri
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    # MONGO_URI = construct_test_mongo_uri() # Reconstruct if needed for tests
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    if not os.environ.get('SECRET_KEY') or Config.SECRET_KEY == 'a_default_secret_key_change_it':
         print("WARNING: SECRET_KEY not set or is default for production!")
    if not MONGO_HOST or not DB_NAME:
         print("WARNING: MongoDB connection details may be incomplete for production!")

config_by_name = dict(
    development=DevelopmentConfig,
    testing=TestingConfig,
    production=ProductionConfig,
    default=DevelopmentConfig
)

def get_config_name():
    return os.getenv('FLASK_ENV', 'default')

def get_config():
    config_name = get_config_name()
    return config_by_name.get(config_name, DevelopmentConfig)