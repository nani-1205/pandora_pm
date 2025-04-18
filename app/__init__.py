# pandora_pm/app/__init__.py
import sys
import os # Import os
from flask import Flask, render_template, session
# Import selected_config AND config_by_name
from config import selected_config, config_by_name
from .extensions import mongo, login_manager, bcrypt
from .models import User, get_projects_collection # Import models needed for index check
from datetime import datetime
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError

# Get the masked URI from config for logging (avoid recalculating)
# This runs when the module is imported
masked_uri_for_log = "Not Set"
if selected_config.MONGO_URI:
    masked_uri_for_log = selected_config.MONGO_URI
    if '@' in masked_uri_for_log:
        uri_parts = masked_uri_for_log.split('@')
        auth_part = uri_parts[0].split('//')
        if len(auth_part) > 1:
             auth_part = auth_part[1]
             if ':' in auth_part:
                 masked_uri_for_log = f"mongodb://****:****@{uri_parts[1]}"
             else:
                 masked_uri_for_log = f"mongodb://****@{uri_parts[1]}"
        else:
             masked_uri_for_log = "mongodb://[masked-auth]@" + uri_parts[1]
    else: # Handle case like mongodb://host/db
        masked_uri_for_log = selected_config.MONGO_URI

def create_app():
    """Application Factory Function"""
    app = Flask(__name__)
    # Load configuration from the selected object
    app.config.from_object(selected_config)

    print("-" * 50)
    print(f"Initializing Flask App with {type(selected_config).__name__}")
    # Use app.config for consistency after loading
    print(f"Database Target: {app.config.get('MONGO_DBNAME')} on {app.config.get('MONGODB_HOST')}:{app.config.get('MONGODB_PORT')}")
    print(f"Debug mode: {app.config.get('DEBUG')}")
    print("-" * 50)

    # --- Add specific checks for Production if needed ---
    # Use the imported config_by_name here
    if isinstance(selected_config, config_by_name['production']):
        print("Production environment Configuration Class loaded. Performing checks...")
        # Check if essential DB connection info is present in the loaded config
        if not app.config.get('MONGO_URI'):
             print("CRITICAL: MONGO_URI is not configured for production. Check environment variables (MONGODB_HOST, DATABASE_NAME).")
             sys.exit("Production Configuration Error: Missing MONGO_URI")
        # Check for default secret key in production
        if not app.config.get('SECRET_KEY') or app.config.get('SECRET_KEY') == 'you-should-really-set-a-secret-key':
             print("CRITICAL: Default SECRET_KEY is being used in production. Please set a strong, unique SECRET_KEY environment variable.")
             sys.exit("Production Configuration Error: Insecure SECRET_KEY")
        # Check for credentials in production (optional, based on policy)
        if not app.config.get('MONGODB_USERNAME') or not app.config.get('MONGODB_PASSWORD'):
            print("WARNING: Production environment is configured without MongoDB username/password.")


    # =======================================
    # Initialize extensions
    # =======================================
    try:
        print("Initializing Flask-PyMongo...")
        # Ensure MONGO_URI exists before initializing
        if not app.config.get('MONGO_URI'):
             print("CRITICAL: Cannot initialize PyMongo because MONGO_URI is not set in the configuration.")
             print("Check MONGODB_HOST and DATABASE_NAME environment variables (and ensure .env is loaded).")
             sys.exit("Configuration Error: MONGO_URI missing")

        mongo.init_app(app)
        # Ping the server on startup to verify the connection and authentication immediately
        print("Pinging MongoDB server...")
        # The ismaster command is cheap and does not require auth.
        mongo.cx.admin.command('ismaster')
        print(f"Successfully connected to MongoDB server at {app.config.get('MONGODB_HOST')}:{app.config.get('MONGODB_PORT')}")
    except ServerSelectionTimeoutError as e:
         print(f"CRITICAL: MongoDB server selection timeout. Could not connect within the time limit.")
         print(f"Attempted connection to: {app.config.get('MONGODB_HOST')}:{app.config.get('MONGODB_PORT')}")
         print(f"Check if MongoDB server is running, accessible, and firewall rules allow connection.")
         print(f"Error details: {e}")
         sys.exit(f"MongoDB Connection Timeout Error: {e}") # Exit gracefully
    except ConnectionFailure as e:
         print(f"CRITICAL: Could not connect to MongoDB.")
         print(f"URI used (masked): {masked_uri_for_log}")
         print(f"Check HOST/PORT/Credentials/Network. Error: {e}")
         sys.exit(f"MongoDB Connection Failure: {e}") # Exit gracefully
    except OperationFailure as e:
        # This often indicates authentication failure
        print(f"CRITICAL: MongoDB operation failure during connection test (likely authentication).")
        print(f"URI used (masked): {masked_uri_for_log}")
        print(f"Check USERNAME/PASSWORD/AUTH_SOURCE ('{app.config.get('MONGODB_USERNAME')}'/'{app.config.get('MONGODB_AUTH_SOURCE')}'). Error details: {e.details}")
        sys.exit(f"MongoDB Authentication/Operation Error: {e}")
    except Exception as e:
        # Catch-all for other unexpected init errors
        print(f"CRITICAL: An unexpected error occurred during MongoDB initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(f"MongoDB Initialization Error: {e}")

    print("Initializing Flask-Login...")
    login_manager.init_app(app)
    print("Initializing Flask-Bcrypt...")
    bcrypt.init_app(app)
    print("Extensions initialized.")


    # =======================================
    # Register Blueprints
    # =======================================
    print("Registering blueprints...")
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from .main import bp as main_bp
    app.register_blueprint(main_bp)
    from .admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    from .projects import bp as projects_bp
    app.register_blueprint(projects_bp, url_prefix='/projects')
    print("Blueprints registered.")


    # =======================================
    # Context Processors
    # =======================================
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow}


    # =======================================
    # Register Error Handlers
    # =======================================
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', title="Forbidden"), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html', title="Page Not Found"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        # Use Flask's built-in logger
        app.logger.error(f"Internal Server Error: {error}", exc_info=sys.exc_info())
        return render_template('errors/500.html', title="Server Error"), 500


    # =======================================
    # Database and Collection Check/Creation
    # =======================================
    with app.app_context():
        try:
            # Ensure mongo.db is available after successful init
            if not mongo or not hasattr(mongo, 'db'):
                 print("CRITICAL: mongo.db not available for database checks.")
                 sys.exit("DB Check Error: mongo object not ready.")

            db_name = mongo.db.name # Get the actual DB name from the connection
            print("-" * 50)
            print(f"Checking Database '{db_name}' and Collections...")

            existing_collections = mongo.db.list_collection_names()
            print(f"Existing collections: {existing_collections}")

            # Define collections and their essential unique/performance indexes
            required_collections = {
                'users': [
                    {'keys': [('username', 1)], 'options': {'name': 'username_unique', 'unique': True}},
                    {'keys': [('email', 1)], 'options': {'name': 'email_unique', 'unique': True}}
                ],
                'projects': [
                    {'keys': [('owner_id', 1)], 'options': {'name': 'project_owner_idx'}},
                    {'keys': [('tasks._id', 1)], 'options': {'name': 'embedded_task_id_idx'}}
                ]
            }

            for coll_name, indexes in required_collections.items():
                print(f"Processing collection: '{coll_name}'")
                collection = mongo.db[coll_name] # Get collection object

                # Ensure Indexes
                print(f"  Ensuring indexes for '{coll_name}'...")

                for index_info in indexes:
                    try:
                        # create_index is idempotent, safe to call even if index exists
                        collection.create_index(index_info['keys'], **index_info['options'])
                        index_name = index_info['options'].get('name', '_'.join([k[0] for k in index_info['keys']]) + '_idx') # Generate name if needed
                        print(f"    - Ensured index: '{index_name}'")
                    except OperationFailure as idx_e:
                            print(f"    - Warning: Could not ensure index {index_info['keys']} (permissions? conflict?): {idx_e.details}")


            print("Database and collection checks complete.")
            print("-" * 50)

        except OperationFailure as op_e:
             print(f"CRITICAL: MongoDB operation failure during startup checks (listCollections/createIndex).")
             print(f"User '{app.config.get('MONGODB_USERNAME')}' might lack permissions on db '{mongo.db.name}' (e.g., readWrite, dbAdmin).")
             print(f"Error details: {op_e.details}")
             sys.exit(f"MongoDB Permission/Operation Failure: {op_e}")
        except Exception as e:
            print(f"CRITICAL: An unexpected error occurred during database/collection check: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(f"DB Check Error: {e}")


    print(f"Flask application '{app.name}' created successfully.")
    return app