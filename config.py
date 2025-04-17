# pandora_pm/config.py
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus # Required for encoding

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '..', '.env') # Path is one level up from app/
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
     # Try loading from current directory if .env is beside config.py (less common setup)
     load_dotenv(os.path.join(basedir, '.env'))


# --- Read individual MongoDB components from environment ---
MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
MONGO_PORT = os.environ.get('MONGO_PORT', '27017')
MONGO_USER = os.environ.get('MONGO_USER') # Returns None if not set
MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD') # Returns None if not set
MONGO_AUTH_DB = os.environ.get('MONGO_AUTH_DB') # Auth source, often 'admin'
DB_NAME = os.environ.get('DB_NAME') or 'pandora_pm_db' # Default database name if not in .env

# --- Construct MONGO_URI ---
mongo_uri = "mongodb://"

# Add credentials if both user and password are provided
if MONGO_USER and MONGO_PASSWORD:
    # *** Encode BOTH username and password using quote_plus ***
    # This is the recommended way by PyMongo to handle special characters.
    encoded_user = quote_plus(MONGO_USER)
    encoded_password = quote_plus(MONGO_PASSWORD)
    mongo_uri += f"{encoded_user}:{encoded_password}@"

# Add host and port
mongo_uri += f"{MONGO_HOST}:{MONGO_PORT}/"

# Add the application database name
mongo_uri += f"{DB_NAME}"

# Add authSource if authentication is enabled and auth source is specified
if MONGO_USER and MONGO_AUTH_DB:
    mongo_uri += f"?authSource={MONGO_AUTH_DB}"

# You can print the constructed URI during development to verify
# print(f"Constructed MONGO_URI: {mongo_uri}")


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    # Use the dynamically constructed MONGO_URI
    MONGO_URI = mongo_uri
    DEBUG = False
    TESTING = False
    # Add other default settings if needed

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # Could potentially override parts for dev DB if needed, but usually inherits

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    # Often uses a different DB_NAME for tests, reconstruct URI if needed
    # Example: MONGO_URI = construct_mongo_uri(DB_NAME='pandora_pm_test_db')
    # (You'd need to wrap the construction logic in a reusable function)
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration."""
    # Ensure necessary vars were set for production construction
    if not os.environ.get('SECRET_KEY'):
         print("WARNING: SECRET_KEY not set for production via environment variables!")
    # MONGO_URI is already constructed based on env vars

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