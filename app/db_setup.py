# app/db_setup.py
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ConfigurationError
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def setup_mongodb():
    """
    Connects using admin credentials to ensure the application database
    and user exist, creating them if necessary.

    Reads configuration from environment variables.
    Returns the connection URI for the application user.
    Raises exceptions on critical failures.
    """
    admin_uri = os.environ.get('MONGO_ADMIN_URI')
    app_db_name = os.environ.get('MONGO_APP_DB_NAME')
    app_user = os.environ.get('MONGO_APP_USER')
    app_pass = os.environ.get('MONGO_APP_PASSWORD')
    app_host = os.environ.get('MONGO_APP_HOST')

    if not all([admin_uri, app_db_name, app_user, app_pass, app_host]):
        log.error("Missing one or more MongoDB environment variables (MONGO_ADMIN_URI, MONGO_APP_DB_NAME, MONGO_APP_USER, MONGO_APP_PASSWORD, MONGO_APP_HOST)")
        raise ConfigurationError("Missing MongoDB configuration in environment variables.")

    admin_client = None
    try:
        log.info(f"Attempting to connect to MongoDB with admin credentials...")
        # Increase timeout slightly for initial connection potentially
        admin_client = MongoClient(admin_uri, serverSelectionTimeoutMS=10000)
        # The ismaster command is cheap and does not require auth.
        admin_client.admin.command('ismaster')
        log.info("MongoDB admin connection successful (pre-auth check).")

        # Check if application user exists
        admin_db = admin_client['admin'] # Need admin role on 'admin' db often
        user_info = admin_db.command('usersInfo', {'user': app_user, 'db': 'admin'}) # Check if user exists in admin db

        user_exists = bool(user_info['users'])

        if user_exists:
            log.info(f"Application user '{app_user}' already exists.")
            # Optional: Check if user has rights on the specific app DB and update if needed
            # This adds complexity, assuming creation implies correct rights for now.
        else:
            log.info(f"Application user '{app_user}' not found. Attempting to create...")
            try:
                # Create the user with roles specifically on the application database
                admin_client[app_db_name].command('createUser', app_user,
                                                  pwd=app_pass,
                                                  roles=[{'role': 'readWrite', 'db': app_db_name}])
                                                  # You might add roles like 'dbAdmin' and 'userAdmin'
                                                  # on app_db_name if the app needs to create collections/indexes dynamically
                                                  # but 'readWrite' is often sufficient for basic CRUD.
                log.info(f"Successfully created user '{app_user}' with readWrite role on database '{app_db_name}'.")

                # Verify creation (optional but good practice)
                user_info_after = admin_db.command('usersInfo', {'user': app_user, 'db': 'admin'})
                if not bool(user_info_after['users']):
                     log.error(f"Failed to verify creation of user '{app_user}'.")
                     raise OperationFailure("User creation verification failed.")

            except OperationFailure as e:
                log.error(f"Failed to create application user '{app_user}': {e}")
                # Check for specific error codes if needed (e.g., auth failure)
                if "AuthenticationFailed" in str(e):
                     log.error("Admin authentication failed. Check MONGO_ADMIN_URI.")
                elif "command createUser requires authentication" in str(e):
                     log.error("Admin user lacks privileges to create users.")
                raise # Re-raise the exception

        # Database Creation Note: MongoDB creates databases implicitly when data
        # (like the user definition or first document) is inserted.
        # We don't strictly need to create the DB itself, but we ensure the user has rights to it.
        # If needed, you could explicitly create a dummy collection:
        # if app_db_name not in admin_client.list_database_names():
        #     log.info(f"Creating dummy collection in '{app_db_name}' to ensure DB exists.")
        #     admin_client[app_db_name]['_dummy_collection'].insert_one({'setup': True})
        #     admin_client[app_db_name]['_dummy_collection'].delete_one({'setup': True})

        # Construct the application user's connection URI
        app_connection_uri = f"mongodb://{app_user}:{app_pass}@{app_host}/{app_db_name}?authSource={app_db_name}"
        # Use authSource=app_db_name if the user was created within that DB's context
        # Use authSource=admin if the user was created in the admin DB but has roles on app_db_name
        # Let's assume creation context implies authSource = app_db_name for simplicity here. Adjust if needed.

        log.info(f"MongoDB setup check complete. Using application URI: mongodb://{app_user}:****@{app_host}/{app_db_name}?authSource={app_db_name}")
        return app_connection_uri

    except ConnectionFailure as e:
        log.error(f"MongoDB admin connection failed: {e}")
        raise
    except OperationFailure as e:
        log.error(f"MongoDB admin operation failed during setup: {e}")
        # This might catch permission errors if admin user isn't admin enough
        raise
    except Exception as e:
        log.error(f"An unexpected error occurred during MongoDB setup: {e}")
        raise
    finally:
        if admin_client:
            admin_client.close()
            log.info("MongoDB admin connection closed.")