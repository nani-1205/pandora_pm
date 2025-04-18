# app/__init__.py
import os
from flask import Flask
from flask_login import current_user # Import current_user proxy
# --- Import extensions from the new file ---
from .extensions import db, login_manager, bcrypt
# --- Other imports ---
from config import Config
import datetime
import logging
from .db_setup import setup_mongodb, ConfigurationError
# Only import constants or base classes from models here at module level
# Full model classes should be imported inside functions where needed if they depend on db
from .models import DEFAULT_THEME, AVAILABLE_THEMES # Import theme constants

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# User loader callback for Flask-Login - Uses login_manager from extensions
@login_manager.user_loader
def load_user(user_id):
    from .models import User # Import User model here when needed
    try:
        return User.objects(pk=user_id).first()
    except Exception as e:
        log.error(f"Error loading user {user_id}: {e}", exc_info=True)
        return None

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    app.config.from_pyfile('config.py', silent=True)

    # --- MongoDB Setup ---
    try:
        log.info("Starting MongoDB setup check...")
        app_mongo_uri = setup_mongodb()
        log.info("Configuring Flask-MongoEngine with application user URI.")
        app.config['MONGODB_SETTINGS'] = {
            'host': app_mongo_uri,
            'connect': False
        }
    except ConfigurationError as e:
        log.error(f"CRITICAL: MongoDB configuration error: {e}")
        raise SystemExit(f"MongoDB configuration error: {e}") from e
    except Exception as e:
        log.error(f"CRITICAL: Failed to setup or connect to MongoDB: {e}")
        raise SystemExit(f"Failed to setup/connect to MongoDB: {e}") from e
    # --- End MongoDB Setup ---

    # Initialize extensions AFTER DB config is set, using imported instances
    log.info("Initializing Flask extensions...")
    try:
        db.init_app(app)
        login_manager.init_app(app)
        bcrypt.init_app(app)
        log.info("Flask extensions initialized.")
    except Exception as e:
         log.error(f"CRITICAL: Failed to initialize Flask extensions: {e}")
         raise SystemExit(f"Failed to initialize Flask extensions: {e}") from e

    # Configure Flask-Login
    login_manager.login_view = 'main.login' # Use blueprint name
    login_manager.login_message_category = 'info'
    login_manager.login_message = "Please log in to access this page."

    with app.app_context():
        # --- Context Processors ---
        @app.context_processor
        def inject_now():
           return {'now': datetime.datetime.utcnow()}

        @app.context_processor
        def inject_theme():
            """Injects the current user's theme CSS filename into templates."""
            try:
                # Ensure User model is imported if needed, though current_user should have theme attr
                # from .models import User
                if current_user.is_authenticated and hasattr(current_user, 'theme') and current_user.theme in AVAILABLE_THEMES:
                    theme_file = f"css/{current_user.theme}.css"
                else:
                    theme_file = f"css/{DEFAULT_THEME}.css"
            except Exception as e:
                log.error(f"Error injecting theme: {e}", exc_info=True)
                theme_file = f"css/{DEFAULT_THEME}.css"
            return dict(current_theme_css=theme_file)
        # --- End Context Processors ---

        log.info("Registering blueprints...")
        from .routes import main_routes # Import the blueprint instance
        app.register_blueprint(main_routes)
        log.info("Blueprints registered.")

        # --- Perform initial DB connection test ---
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
        # --- End DB connection test ---

    log.info("Application creation completed.")
    return app