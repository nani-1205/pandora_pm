# pandora_pm/run.py
import os
import click
from app import create_app
from app.extensions import mongo
from app.models import User
from config import get_config_name
from datetime import datetime # Needed for init-admin command

config_name = get_config_name()
app = create_app(config_name)

# --- Flask CLI Command to Create Initial Admin ---
@app.cli.command("init-admin")
@click.option('--username', default=lambda: os.environ.get('PANDORA_ADMIN_USERNAME', 'admin'), help='Admin username.')
@click.option('--email', default=lambda: os.environ.get('PANDORA_ADMIN_EMAIL', None), help='Admin email.')
@click.option('--password', default=lambda: os.environ.get('PANDORA_ADMIN_PASSWORD', None), help='Admin password.')
def init_admin(username, email, password):
    """Creates the initial admin user if none exists or prompts if needed."""
    with app.app_context():
        if mongo.db.users.count_documents({'role': 'admin'}) > 0:
            click.echo('Admin user already exists. Skipping creation.')
            return

        click.echo('No admin user found. Creating initial admin...')

        if not email:
             email = click.prompt('Enter admin email')
        if not password:
             password = click.prompt('Enter admin password', hide_input=True, confirmation_prompt=True)

        if not all([username, email, password]):
            click.echo('Username, email, and password are required. Aborting.')
            return

        # Basic validation
        if '@' not in email or '.' not in email:
             click.echo('Invalid email format. Aborting.')
             return

        # Create admin user
        admin_user = User.create(username=username, email=email, password=password, role='admin')

        if admin_user:
            click.echo(f"Admin user '{username}' created successfully!")
        else:
            # Check if maybe user exists but isn't admin (shouldn't happen with above check)
            existing = User.find_by_username(username) or User.find_by_email(email)
            if existing:
                 click.echo(f"Failed to create admin. User '{username}' or email '{email}' already exists but may not be admin.")
            else:
                 click.echo('Failed to create admin user. Check database connection and logs.')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])