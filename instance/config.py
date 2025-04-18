# instance/config.py
# !!! IMPORTANT: Add 'instance/' folder to your .gitignore file !!!
# This file is NOT meant to be committed to version control.
# It holds sensitive or instance-specific configuration overrides.

import os

# --- Production/Sensitive Overrides ---

# Example: Override the SECRET_KEY for production (use a strong, randomly generated key)
# SECRET_KEY = 'a_much_stronger_and_different_secret_key_for_production'

# Example: Override the MongoDB URI for a production database (e.g., MongoDB Atlas)
# MONGODB_SETTINGS = {
#     'host': os.environ.get('PROD_MONGODB_URI') or 'mongodb+srv://user:password@your_cluster.mongodb.net/avatar_pm_prod_db?retryWrites=true&w=majority'
# }

# You only need to define the settings you want to OVERRIDE from the main config.py
# If a setting is not defined here, the value from the main config.py will be used.

# Example: If you are using environment variables for secrets (recommended),
# you might not need much in this file, but it's still good practice
# to configure Flask to look for it. You could potentially set
# other non-sensitive instance-specific things here if needed.

# For Development (using values from .env via main config.py is usually sufficient)
# You might leave this file empty or just add comments during development,
# knowing it's ready for production overrides later.

# Development Example (if you wanted to force a different dev DB *without* changing .env)
# SECRET_KEY = 'dev-secret-key-override'
# MONGODB_SETTINGS = {
#    'host': 'mongodb://localhost:27017/avatar_pm_db_instance_override'
# }