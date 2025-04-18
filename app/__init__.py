# pandora_pm/app/__init__.py
import os
from flask import Flask, render_template
from config import config_by_name
from .extensions import mongo, login_manager, bcrypt
from datetime import datetime # Import datetime

def create_app(config_name=None):
    """Application Factory Function"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    mongo.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Register Blueprints
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    from .admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from .projects import bp as projects_bp
    app.register_blueprint(projects_bp, url_prefix='/projects')

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', title='Forbidden'), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html', title='Page Not Found'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        # Log the error in production
        # app.logger.error(f'Server Error: {error}', exc_info=True)
        return render_template('errors/500.html', title='Server Error'), 500

    # Context processor to inject variables into all templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()} # For footer copyright year

    return app