# pandora_pm/app/__init__.py
from flask import Flask, render_template, session
from config import get_config, selected_config
from .extensions import mongo, login_manager, bcrypt
from datetime import datetime

def create_app():
    """Application Factory Function"""
    app = Flask(__name__)
    app.config.from_object(selected_config) # Use the pre-selected config

    # Initialize extensions
    mongo.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Register Blueprints
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from .main import bp as main_bp
    app.register_blueprint(main_bp) # No prefix for main routes like dashboard

    from .admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from .projects import bp as projects_bp
    app.register_blueprint(projects_bp, url_prefix='/projects')

    # --- Context Processors ---
    # Make variables available to all templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow}

    # --- Register Error Handlers ---
    # Make sure templates/errors/ directory exists with 403.html, 404.html, 500.html
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', title="Forbidden"), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html', title="Page Not Found"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        # Log the error in a real app
        print(f"Server Error: {error}")
        # Optional: Rollback DB session if using transactions
        return render_template('errors/500.html', title="Server Error"), 500

    with app.app_context():
        # Ensure indexes are created on startup (important for performance and uniqueness)
        # Adjust index creation as needed based on your queries
        User.get_collection().create_index('username', unique=True)
        User.get_collection().create_index('email', unique=True)
        get_projects_collection().create_index('owner_id')
        get_projects_collection().create_index('tasks._id') # Index embedded task IDs
        print("Database indexes ensured.")


    print(f"App created with config: {type(selected_config).__name__}")
    return app