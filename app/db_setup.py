# app/db_setup.py
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ConfigurationError
import logging
from urllib.parse import quote_plus # To handle special characters in passwords/usernames if needed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    app_host = os.environ.get('MONGO_APP_HOST') # e.g., '18.60.186.55:27017'

    if not all([admin_uri, app_db_name, app_user, app_pass, app_host]):
        log.error("Missing one or more MongoDB environment variables (MONGO_ADMIN_URI, MONGO_APP_DB_NAME, MONGO_APP_USER, MONGO_APP_PASSWORD, MONGO_APP_HOST)")
        raise ConfigurationError("Missing MongoDB configuration in environment variables.")

    admin_client = None
    try:
        log.info(f"Attempting to connect to MongoDB at {app_host} with admin credentials...")
        # Increase timeout slightly for initial connection potentially
        admin_client = MongoClient(admin_uri, serverSelectionTimeoutMS=10000)
        # The ismaster command is cheap and does not require auth. Check server reachability.
        admin_client.admin.command('ismaster')
        log.info("MongoDB admin connection successful (pre-auth check completed).")

        # --- Check if application user exists IN THE APPLICATION DATABASE ---
        user_exists = False
        log.info(f"Checking for user '{app_user}' in database '{app_db_name}'...")
        try:
            # Connect to the target app database context using the admin client
            app_db_context = admin_client[app_db_name]
            # Check for the user associated with app_db_name
            # This requires the admin user to have sufficient privileges (like listusers on any db, or specific on this db)
            user_info = app_db_context.command('usersInfo', {'user': app_user, 'db': app_db_name})
            user_exists = bool(user_info['users'])
            if user_exists:
                log.info(f"Application user '{app_user}' already exists in database '{app_db_name}'.")

        except OperationFailure as e:
            # Handle cases where the database might not exist yet OR insufficient privileges for usersInfo
            # Error code 13: Unauthorized. If the admin user cannot check usersInfo on app_db_name.
            # Other errors might mean the DB doesn't exist.
            # If the check itself fails, we can cautiously proceed assuming the user *might* not exist,
            # letting the createUser command handle the "already exists" error if necessary.
            log.warning(f"Could not execute usersInfo command on '{app_db_name}' (maybe DB/user doesn't exist yet, or insufficient admin privileges?): {e}")
            user_exists = False # Proceed with creation attempt cautiously

        # --- Create user if it doesn't exist ---
        if not user_exists:
            log.info(f"Application user '{app_user}' not found in '{app_db_name}' (or check failed). Attempting to create...")
            try:
                # Ensure we're using the application DB context for creation
                app_db_creation_context = admin_client[app_db_name]
                app_db_creation_context.command('createUser', app_user,
                                                pwd=app_pass,
                                                roles=[{'role': 'readWrite', 'db': app_db_name}])
                                                # Add other roles like dbAdmin/userAdmin on app_db_name if needed
                log.info(f"Successfully created user '{app_user}' with readWrite role on database '{app_db_name}'.")

                # Optional: Verify creation again after the attempt
                # user_info_after = app_db_creation_context.command('usersInfo', {'user': app_user, 'db': app_db_name})
                # if not bool(user_info_after['users']):
                #     log.error(f"Failed to verify creation of user '{app_user}' after attempt.")
                #     raise OperationFailure("User creation verification failed.")

            except OperationFailure as e:
                # Catch the specific "already exists" error, which might happen if the initial check failed wrongly
                if 'User' in str(e) and 'already exists' in str(e):
                    log.warning(f"User '{app_user}@{app_db_name}' already exists (createUser command confirmed). Proceeding.")
                elif "AuthenticationFailed" in str(e):
                     log.error(f"Admin authentication failed. Check MONGO_ADMIN_URI credentials. Error: {e}")
                     raise # Re-raise critical auth error
                elif "command createUser requires authentication" in str(e) or "not authorized" in str(e).lower():
                     log.error(f"Admin user lacks privileges to create users on '{app_db_name}'. Error: {e}")
                     raise # Re-raise critical privilege error
                else:
                    # Raise other unexpected OperationFailures during creation
                    log.error(f"Failed to create application user '{app_user}': {e}")
                    raise # Re-raise other creation errors

        # --- Construct the application user's connection URI ---
        # URL Encode username/password just in case they contain special chars like '@', ':', '/'
        encoded_user = quote_plus(app_user)
        encoded_pass = quote_plus(app_pass)

        # Use authSource=app_db_name since the user is defined within that database's context
        app_connection_uri = f"mongodb://{encoded_user}:{encoded_pass}@{app_host}/{app_db_name}?authSource={app_db_name}"

        log.info(f"MongoDB setup check complete. Using application URI: mongodb://{encoded_user}:****@{app_host}/{app_db_name}?authSource={app_db_name}")
        return app_connection_uri

    except ConfigurationError as e:
        log.error(f"Configuration Error: {e}")
        raise # Re-raise config errors
    except ConnectionFailure as e:
        log.error(f"MongoDB admin connection failed to {app_host}: {e}")
        raise # Re-raise connection errors
    except OperationFailure as e:
        # Catch any operation failures not handled within the specific checks/creation blocks
        log.error(f"MongoDB admin operation failed during setup: {e}")
        raise
    except Exception as e:
        # Catch any other unexpected errors
        log.error(f"An unexpected error occurred during MongoDB setup: {e}", exc_info=True) # Log traceback
        raise
    finally:
        # Ensure the admin client connection is always closed
        if admin_client:
            admin_client.close()
            log.info("MongoDB admin connection closed.")