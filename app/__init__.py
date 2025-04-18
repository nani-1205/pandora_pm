# app/__init__.py
import os
from flask import Flask
from flask_mongoengine import MongoEngine
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from config import Config
import datetime
import logging

# --- Import the setup function ---
from .db_setup import setup_mongodb, ConfigurationError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Define extensions at the module level
db = MongoEngine()
login_manager = LoginManager()
bcrypt = Bcrypt()

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    # Import models here only when needed to avoid potential early import issues
    from .models import User
    return User.objects(pk=user_id).first()

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    # Load instance config if exists (might contain overrides for SECRET_KEY etc)
    app.config.from_pyfile('config.py', silent=True)

    # --- MongoDB Setup ---
    try:
        log.info("Starting MongoDB setup check...")
        # Call the setup function which reads env variables
        app_mongo_uri = setup_mongodb()

        # --- Configure MongoEngine with the APPLICATION URI ---
        log.info("Configuring Flask-MongoEngine with application user URI.")
        app.config['MONGODB_SETTINGS'] = { # Flask-MongoEngine uses MONGODB_SETTINGS dict
            'host': app_mongo_uri,
            'connect': False # Explicitly set connect=False initially, MongoEngine connects on first query
        }
        # Alternatively, if using MONGODB_HOST directly was intended (check Flask-MongoEngine docs):
        # app.config['MONGODB_HOST'] = app_mongo_uri

    except ConfigurationError as e:
        log.error(f"CRITICAL: MongoDB configuration error: {e}")
        raise SystemExit(f"MongoDB configuration error: {e}") from e
    except Exception as e:
        log.error(f"CRITICAL: Failed to setup or connect to MongoDB: {e}")
        raise SystemExit(f"Failed to setup/connect to MongoDB: {e}") from e
    # --- End MongoDB Setup ---


    # Initialize extensions AFTER DB config is set
    log.info("Initializing Flask extensions...")
    try:
        db.init_app(app) # Now db uses the configured settings
        login_manager.init_app(app)
        bcrypt.init_app(app)
        log.info("Flask extensions initialized.")
    except Exception as e:
         log.error(f"CRITICAL: Failed to initialize Flask extensions (check DB connection string?): {e}")
         raise SystemExit(f"Failed to initialize Flask extensions: {e}") from e


    # Configure Flask-Login
    login_manager.login_view = 'main.login' # <<<--- Use blueprint name here
    login_manager.login_message_category = 'info'
    login_manager.login_message = "Please log in to access this page."

    with app.app_context():
        # Register context processors here if needed
        @app.context_processor
        def inject_now():
           return {'now': datetime.datetime.utcnow()}

        # --- Register Blueprints ---
        log.info("Registering blueprints...")
        from .routes import main_routes # Import the blueprint instance
        app.register_blueprint(main_routes)
        # If you had other blueprints (e.g., for API), register them here too
        # from .api import api_bp
        # app.register_blueprint(api_bp, url_prefix='/api')
        log.info("Blueprints registered.")

        # Perform check to ensure DB connection works with app credentials
        try:
            log.info("Performing initial DB connection test with app credentials...")
            from .models import User # Import here for the check
            user_count = User.objects.count() # Example check
            log.info(f"DB connection test successful. Found {user_count} users.")
        except Exception as e:
            log.error(f"CRITICAL: Failed to connect/interact with MongoDB using application credentials: {e}")
            log.error(f"Check connection settings: {app.config.get('MONGODB_SETTINGS', 'Not Set')}")
            log.error("Verify firewall rules, user permissions on the database, and authSource.")
            raise SystemExit(f"Failed DB connection test: {e}") from e

        log.info("Application creation completed.")
        return app