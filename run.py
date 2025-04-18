# pandora_pm/run.py
import os
from app import create_app

# Create the Flask app instance using the factory
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Debug mode is controlled by FLASK_ENV/config now
    # Host 0.0.0.0 makes it accessible on your network
    app.run(host='0.0.0.0', port=port)