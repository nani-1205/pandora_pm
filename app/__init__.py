# pandora_pm/app/__init__.py
import sys
from flask import Flask, render_template, session
from config import get_config, selected_config
from .extensions import mongo, login_manager, bcrypt
from .models import User, get_projects_collection # Import models needed for index check
from datetime import datetime
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError

def create_app():
    """Application Factory Function"""
    app = Flask(__name__)
    app.config.from_object(selected_config) # Use the pre-selected config

    print("-" * 50)
    print(f"Initializing Flask App with {type(selected_config).__name__}")
    print(f"Database Target: {selected_config.MONGO_DBNAME} on {selected_config.MONGODB_HOST}:{selected_config.MONGODB_PORT}")
    print("-" * 50)


    # =======================================
    # Initialize extensions
    # =======================================
    try:
        print("Initializing Flask-PyMongo...")
        mongo.init_app(app)
        # Ping the server on startup to verify the connection and authentication immediately
        print("Pinging MongoDB server...")
        # The ismaster command is cheap and does not require auth.
        mongo.cx.admin.command('ismaster')
        # For authenticated check, listDatabases might be better if user has permissions
        # Or perform a simple operation on the target DB
        # mongo.db.command('ping') # Requires auth on the target DB
        print(f"Successfully connected to MongoDB server at {selected_config.MONGODB_HOST}:{selected_config.MONGODB_PORT}")
    except ServerSelectionTimeoutError as e:
         print(f"CRITICAL: MongoDB server selection timeout. Could not connect within the time limit.")
         print(f"Attempted connection to: {selected_config.MONGODB_HOST}:{selected_config.MONGODB_PORT}")
         print(f"Check if MongoDB server is running, accessible, and firewall rules allow connection.")
         print(f"Error details: {e}")
         sys.exit(f"MongoDB Connection Timeout Error: {e}") # Exit gracefully
    except ConnectionFailure as e:
         print(f"CRITICAL: Could not connect to MongoDB.")
         print(f"URI used (masked): {masked_uri}") # Use the masked URI from config.py if needed
         print(f"Check HOST/PORT/Credentials/Network. Error: {e}")
         sys.exit(f"MongoDB Connection Failure: {e}") # Exit gracefully
    except OperationFailure as e:
        # This often indicates authentication failure
        print(f"CRITICAL: MongoDB operation failure during connection test (likely authentication).")
        print(f"URI used (masked): {masked_uri}")
        print(f"Check USERNAME/PASSWORD/AUTH_SOURCE ('{selected_config.MONGODB_USERNAME}'/'{selected_config.MONGODB_AUTH_SOURCE}'). Error details: {e.details}")
        sys.exit(f"MongoDB Authentication/Operation Error: {e}")
    except Exception as e:
        # Catch-all for other unexpected init errors
        print(f"CRITICAL: An unexpected error occurred during MongoDB initialization: {e}")
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
        # Log the occurrence if needed
        # app.logger.warning(f"Forbidden access attempt: {request.path}")
        return render_template('errors/403.html', title="Forbidden"), 403

    @app.errorhandler(404)
    def page_not_found(error):
        # app.logger.warning(f"404 Not Found: {request.path}")
        return render_template('errors/404.html', title="Page Not Found"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        # Log the full error and stack trace in production
        app.logger.error(f"Internal Server Error: {error}", exc_info=sys.exc_info())
        # Optional: Rollback DB session if using transactions (not typical with basic PyMongo)
        return render_template('errors/500.html', title="Server Error"), 500


    # =======================================
    # Database and Collection Check/Creation
    # =======================================
    with app.app_context():
        try:
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
                    {'keys': [('tasks._id', 1)], 'options': {'name': 'embedded_task_id_idx'}} # Index embedded task IDs
                    # Add index for project name if frequently queried:
                    # {'keys': [('name', 1)], 'options': {'name':'project_name_idx'}},
                ]
                # Add other collections (e.g., 'tasks' if not embedded) and indexes here
                # 'tasks': [
                #     {'keys': [('project_id', 1)], 'options': {'name': 'task_project_ref_idx'}},
                #     {'keys': [('assigned_to', 1)], 'options': {'name': 'task_assignee_idx'}},
                #     {'keys': [('status', 1)], 'options': {'name': 'task_status_idx'}},
                # ]
            }

            for coll_name, indexes in required_collections.items():
                print(f"Processing collection: '{coll_name}'")
                if coll_name not in existing_collections:
                    # MongoDB creates collections lazily, but we ensure indexes immediately
                    print(f"  Collection '{coll_name}' not found. Ensuring indexes (will create collection if needed)...")
                    for index_info in indexes:
                        try:
                             mongo.db[coll_name].create_index(index_info['keys'], **index_info['options'])
                             print(f"    - Created index '{index_info['options'].get('name', str(index_info['keys']))}'")
                        except OperationFailure as idx_e:
                             # This could happen if created concurrently or due to permission issues
                             print(f"    - Warning: Could not create index {index_info['keys']} (maybe check permissions?): {idx_e.details}")
                else:
                    # Ensure indexes exist even if collection exists
                    print(f"  Collection '{coll_name}' exists. Ensuring indexes...")
                    current_indexes = mongo.db[coll_name].index_information()
                    # print(f"    Current indexes: {current_indexes}") # Debug print
                    for index_info in indexes:
                        index_name = index_info['options'].get('name')
                        # Check if an index with the desired name already exists
                        if index_name and index_name in current_indexes:
                             # print(f"    - Index '{index_name}' already exists.")
                             pass # Index exists, assume it's correct (more complex checks possible)
                        else:
                             # Attempt to create index if name not found (or if no name specified in our config)
                             try:
                                mongo.db[coll_name].create_index(index_info['keys'], **index_info['options'])
                                print(f"    - Ensured index: '{index_info['options'].get('name', str(index_info['keys']))}'")
                             except OperationFailure as idx_e:
                                  print(f"    - Warning: Could not ensure index {index_info['keys']} (permissions? conflict?): {idx_e.details}")


            print("Database and collection checks complete.")
            print("-" * 50)

        except OperationFailure as op_e:
             # This might indicate permission issues (e.g., cannot run listCollections or createIndex)
             print(f"CRITICAL: MongoDB operation failure during startup checks.")
             print(f"User '{selected_config.MONGODB_USERNAME}' might lack permissions on db '{mongo.db.name}' (e.g., readWrite, dbAdmin).")
             print(f"Error details: {op_e.details}")
             sys.exit(f"MongoDB Permission/Operation Failure: {op_e}")
        except Exception as e:
            # Catch other potential errors during the check phase
            print(f"CRITICAL: An unexpected error occurred during database/collection check: {e}")
            # Log the full traceback here in a real app
            import traceback
            traceback.print_exc()
            sys.exit(f"DB Check Error: {e}")


    print(f"Flask application '{app.name}' created successfully.")
    return app

# Make the masked URI available outside the function if needed (though selected_config should be preferred)
# Note: This runs when the module is imported, selected_config is better practice.
masked_uri = selected_config.MONGO_URI
if '@' in masked_uri:
    uri_parts = masked_uri.split('@')
    auth_part = uri_parts[0].split('//')[1]
    if ':' in auth_part:
         masked_uri = f"mongodb://****:****@{uri_parts[1]}"
    else:
        masked_uri = f"mongodb://****@{uri_parts[1]}"
# print(f"Module level masked URI: {masked_uri}") # For debugging import phase