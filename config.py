# pandora_pm/config.py
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus # For safely encoding username/password

# --- Corrected .env Path Loading ---
# Look for .env in the parent directory of this config file (i.e., the project root)
basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.dirname(basedir) # Go up one level from app/ to pandora_pm/
dotenv_path = os.path.join(project_root, '.env') # Look for .env in the project root

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f".env file loaded successfully from {dotenv_path}")
else:
     # Also check if running via PM2, check PM2's cwd if possible
     pm2_cwd = os.getenv('PM2_PROJECT_CWD') # PM2 might set this
     if pm2_cwd and os.path.exists(os.path.join(pm2_cwd, '.env')):
         load_dotenv(os.path.join(pm2_cwd, '.env'))
         print(f".env file loaded successfully from PM2 CWD: {os.path.join(pm2_cwd, '.env')}")
     else:
         # Use the project_root path in the warning
         print(f"Warning: .env file not found at primary path: {dotenv_path}")
         if pm2_cwd:
             print(f"Warning: Also checked PM2 CWD path: {os.path.join(pm2_cwd, '.env')}")


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-should-really-set-a-secret-key' # Keep default for safety

    # Read individual MongoDB components from environment
    MONGODB_USERNAME = os.environ.get('MONGODB_USERNAME')
    MONGODB_PASSWORD = os.environ.get('MONGODB_PASSWORD')
    MONGODB_HOST = os.environ.get('MONGODB_HOST') # No default 'localhost' here, force setting it
    MONGODB_PORT = os.environ.get('MONGODB_PORT', '27017')
    DATABASE_NAME = os.environ.get('DATABASE_NAME') # No default here, force setting it
    MONGODB_AUTH_SOURCE = os.environ.get('MONGODB_AUTH_SOURCE', 'admin') # Defaults to 'admin'

    # Dynamically construct the MONGO_URI
    MONGO_URI = None # Initialize to None
    if MONGODB_HOST and DATABASE_NAME: # Only construct if essential parts are present
        if MONGODB_USERNAME and MONGODB_PASSWORD:
            # Ensure username/password characters are URL-encoded if necessary
            encoded_username = quote_plus(MONGODB_USERNAME)
            encoded_password = quote_plus(MONGODB_PASSWORD)
            MONGO_URI = (
                f"mongodb://{encoded_username}:{encoded_password}@"
                f"{MONGODB_HOST}:{MONGODB_PORT}/{DATABASE_NAME}"
                f"?authSource={MONGODB_AUTH_SOURCE}"
            )
        elif MONGODB_USERNAME: # Handle username only case if applicable (less common, might need authSource)
             encoded_username = quote_plus(MONGODB_USERNAME)
             MONGO_URI = (
                f"mongodb://{encoded_username}@"
                f"{MONGODB_HOST}:{MONGODB_PORT}/{DATABASE_NAME}"
                f"?authSource={MONGODB_AUTH_SOURCE}"
            )
        else:
            # URI for unauthenticated connection
            MONGO_URI = f"mongodb://{MONGODB_HOST}:{MONGODB_PORT}/{DATABASE_NAME}"
    else:
        # Handle case where essential DB config is missing
        print("Warning: MONGODB_HOST or DATABASE_NAME not found in environment. MONGO_URI not constructed.")


    # Flask-PyMongo uses MONGO_URI primarily, but we keep DB name easily accessible
    MONGO_DBNAME = DATABASE_NAME

    DEBUG = False
    TESTING = False
    # Add other default settings if needed


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    print("Loading Development Configuration")


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    # Override database name for tests
    DATABASE_NAME = os.environ.get('TEST_DATABASE_NAME') or 'pandora_pm_test_db'
    MONGO_DBNAME = DATABASE_NAME
    print(f"Loading Testing Configuration - Using DB: {DATABASE_NAME}")

    # Reconstruct MONGO_URI for testing db, using base credentials if provided
    if Config.MONGODB_HOST: # Check if host is set before constructing
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
    else:
         MONGO_URI = None # Cannot construct test URI without host
         print("Warning: TestingConfig cannot construct MONGO_URI because MONGODB_HOST is not set.")

    WTF_CSRF_ENABLED = False # Often disable CSRF for tests


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False # Ensure Debug is off
    TESTING = False # Ensure Testing is off
    print("Loading Production Configuration")

    # Production checks moved to create_app


# Dictionary to easily select config based on environment variable
config_by_name = dict(
    development=DevelopmentConfig,
    testing=TestingConfig,
    production=ProductionConfig,
    default=DevelopmentConfig # Default to Development
)

def get_config():
    """Returns the appropriate config class based on FLASK_ENV."""
    # Default to development if FLASK_ENV is not set
    env = os.getenv('FLASK_ENV', 'development').lower()
    config_class = config_by_name.get(env, DevelopmentConfig)
    print(f"Selected configuration environment: '{env}' -> Using config class: {config_class.__name__}")
    return config_class

# Expose the selected config object directly
selected_config = get_config()

# Optional: Add a final print statement to show the constructed URI (masked)
if selected_config.MONGO_URI:
    masked_uri = selected_config.MONGO_URI
    if '@' in masked_uri:
        uri_parts = masked_uri.split('@')
        auth_part = uri_parts[0].split('//')
        if len(auth_part) > 1:
             auth_part = auth_part[1] # Get the part after //
             if ':' in auth_part:
                 masked_uri = f"mongodb://****:****@{uri_parts[1]}"
             else:
                 masked_uri = f"mongodb://****@{uri_parts[1]}"
        else:
             masked_uri = "mongodb://[masked-auth]@" + uri_parts[1]
    else: # Handle case like mongodb://host/db
         masked_uri = selected_config.MONGO_URI

    print(f"Final MONGO_URI (masked): {masked_uri}")
else:
     print("Final MONGO_URI: Not constructed (Check MONGODB_HOST/DATABASE_NAME in environment)")

print(f"Final Database Name: {selected_config.MONGO_DBNAME or 'Not Set (Check DATABASE_NAME in environment)'}")
print(f"Debug Mode: {selected_config.DEBUG}")
print(f"Secret Key Set: {'Yes' if selected_config.SECRET_KEY and selected_config.SECRET_KEY != 'you-should-really-set-a-secret-key' else 'No / Default (Set SECRET_KEY in environment)'}")