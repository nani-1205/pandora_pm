# pandora_pm/app/decorators.py
from functools import wraps
from flask import abort
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function

# Example: Decorator to check if user owns the project (or is admin)
def project_owner_required(f):
     @wraps(f)
     def decorated_function(*args, **kwargs):
        from .models import get_project_by_id # Local import
        project_id = kwargs.get('project_id')
        if not project_id:
             abort(404) # Or internal server error if route setup is wrong

        project = get_project_by_id(project_id)
        if not project:
             abort(404)

        # Allow access if user is authenticated, and (is admin OR owns the project)
        if not current_user.is_authenticated or \
           (not current_user.is_admin and str(project.get('owner_id')) != current_user.id):
             abort(403)

        # Add project object to kwargs so the view function can use it? Optional.
        # kwargs['project'] = project
        return f(*args, **kwargs)
     return decorated_function