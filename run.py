# pandora_pm/run.py
import os
from app import create_app
from config import get_config_name # Import helper to get env name

# Get the configuration object based on FLASK_ENV
# create_app will load the .env file via the config module
config_name = get_config_name()
app = create_app(config_name)


if __name__ == '__main__':
    # Use the port specified by the environment variable PORT (common for deployment platforms)
    # Default to 5000 for local development
    port = int(os.environ.get('PORT', 5000))
    # Run in debug mode if FLASK_ENV is development (or if DEBUG is True in config)
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])