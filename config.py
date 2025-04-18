# pandora_pm/config.py
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus # For safely encoding username/password

# Load environment variables from .env file located in the parent directory
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f".env file loaded successfully from {dotenv_path}")
else:
     print(f"Warning: .env file not found at {dotenv_path}")

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-should-really-set-a-secret-key'

    # Read individual MongoDB components from environment
    MONGODB_USERNAME = os.environ.get('MONGODB_USERNAME')
    MONGODB_PASSWORD = os.environ.get('MONGODB_PASSWORD')
    MONGODB_HOST = os.environ.get('MONGODB_HOST', 'localhost')
    MONGODB_PORT = os.environ.get('MONGODB_PORT', '27017')
    DATABASE_NAME = os.environ.get('DATABASE_NAME', 'pandora_pm_default_db')
    MONGODB_AUTH_SOURCE = os.environ.get('MONGODB_AUTH_SOURCE', 'admin') # Defaults to 'admin'

    # Dynamically construct the MONGO_URI
    if MONGODB_USERNAME and MONGODB_PASSWORD:
        # Ensure username/password characters are URL-encoded if necessary
        encoded_username = quote_plus(MONGODB_USERNAME)
        encoded_password = quote_plus(MONGODB_PASSWORD)
        MONGO_URI = (
            f"mongodb://{encoded_username}:{encoded_password}@"
            f"{MONGODB_HOST}:{MONGODB_PORT}/{DATABASE_NAME}"
            f"?authSource={MONGODB_AUTH_SOURCE}"
        )
        print(f"Connecting to MongoDB with user '{MONGODB_USERNAME}' on authSource '{MONGODB_AUTH_SOURCE}'")
    elif MONGODB_USERNAME: # Handle username only case if applicable (less common, might need authSource)
         encoded_username = quote_plus(MONGODB_USERNAME)
         MONGO_URI = (
            f"mongodb://{encoded_username}@"
            f"{MONGODB_HOST}:{MONGODB_PORT}/{DATABASE_NAME}"
            f"?authSource={MONGODB_AUTH_SOURCE}"
        )
         print(f"Connecting to MongoDB with user '{MONGODB_USERNAME}' (no password) on authSource '{MONGODB_AUTH_SOURCE}'")
    else:
        # URI for unauthenticated connection
        MONGO_URI = f"mongodb://{MONGODB_HOST}:{MONGODB_PORT}/{DATABASE_NAME}"
        print(f"Connecting to MongoDB without authentication.")

    # Flask-PyMongo uses MONGO_URI primarily, but we keep DB name easily accessible
    MONGO_DBNAME = DATABASE_NAME

    DEBUG = False
    TESTING = False
    # Add other default settings if needed


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # Development usually uses the main Config settings derived from .env
    print("Loading Development Configuration")


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    # Override database name for tests
    DATABASE_NAME = os.environ.get('TEST_DATABASE_NAME') or 'pandora_pm_test_db'
    print(f"Loading Testing Configuration - Using DB: {DATABASE_NAME}")

    # Reconstruct MONGO_URI for testing db, using base credentials if provided
    if Config.MONGODB_USERNAME and Config.MONGODB_PASSWORD:
        encoded_username = quote_plus(Config.MONGODB_USERNAME)
        encoded_password = quote_plus(Config.MONGODB_PASSWORD)
        MONGO_URI = (
            f"mongodb://{encoded_username}:{encoded_password}@"
            f"{Config.MONGODB_HOST}:{Config.MONGODB_PORT}/{DATABASE_NAME}"
            f"?authSource={Config.MONGODB_AUTH_SOURCE}"
        )
    else:
        MONGO_URI = f"mongodb://{Config.MONGODB_HOST}:{Config.MONGODB_PORT}/{DATABASE_NAME}"

    MONGO_DBNAME = DATABASE_NAME
    WTF_CSRF_ENABLED = False # Often disable CSRF for tests


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False # Ensure Debug is off
    TESTING = False # Ensure Testing is off
    print("Loading Production Configuration")

    # Ensure critical variables are set for production
    if not Config.MONGODB_HOST or not Config.DATABASE_NAME or not Config.SECRET_KEY or Config.SECRET_KEY == 'you-should-really-set-a-secret-key':
         raise ValueError("CRITICAL: MONGODB_HOST, DATABASE_NAME, and a non-default SECRET_KEY must be set for production")

    # Production should absolutely require credentials usually
    if not Config.MONGODB_USERNAME or not Config.MONGODB_PASSWORD:
         print("WARNING: Running production environment without MongoDB username/password set in environment variables.")
         # Depending on security policy, you might raise ValueError here too.
         # raise ValueError("CRITICAL: MONGODB_USERNAME and MONGODB_PASSWORD must be set for production")


# Dictionary to easily select config based on environment variable
config_by_name = dict(
    development=DevelopmentConfig,
    testing=TestingConfig,
    production=ProductionConfig,
    default=DevelopmentConfig
)

def get_config():
    """Returns the appropriate config class based on FLASK_ENV."""
    env = os.getenv('FLASK_ENV', 'default')
    config_class = config_by_name.get(env.lower(), DevelopmentConfig)
    print(f"Selected configuration environment: '{env}' -> Using config class: {config_class.__name__}")
    return config_class

# Expose the selected config object directly
selected_config = get_config()

# Optional: Add a final print statement to show the constructed URI (masked)
masked_uri = selected_config.MONGO_URI
if '@' in masked_uri:
    uri_parts = masked_uri.split('@')
    auth_part = uri_parts[0].split('//')[1]
    if ':' in auth_part:
         masked_uri = f"mongodb://****:****@{uri_parts[1]}"
    else:
        masked_uri = f"mongodb://****@{uri_parts[1]}"

print(f"Final MONGO_URI (masked): {masked_uri}")
print(f"Final Database Name: {selected_config.MONGO_DBNAME}")