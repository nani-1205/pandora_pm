# pandora_pm/app/decorators.py
from functools import wraps
from flask import abort, redirect, url_for, request, flash
from flask_login import current_user
from .models import get_project_by_id # Relative import
from bson import ObjectId, errors as bson_errors

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
             flash('Please log in to access this page.', 'info')
             return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def project_owner_required(f):
     @wraps(f)
     def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login', next=request.url))

        project_id = kwargs.get('project_id')
        if not project_id: abort(500)

        project = get_project_by_id(project_id)
        if not project: abort(404)

        # Allow access ONLY if user is admin OR owns the project
        if not current_user.is_admin and str(project.get('owner_id')) != current_user.id:
             abort(403)
        return f(*args, **kwargs)
     return decorated_function

def project_access_required(f):
    """Allows access if user is admin, owner, or assigned to any task in the project."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login', next=request.url))

        project_id = kwargs.get('project_id')
        if not project_id: abort(500)

        project = get_project_by_id(project_id)
        if not project: abort(404)

        is_owner = str(project.get('owner_id')) == current_user.id
        is_admin = current_user.is_admin
        is_assigned = False
        try:
            user_obj_id = ObjectId(current_user.id)
            tasks = project.get('tasks', [])
            if tasks:
                for task in tasks:
                    # Check if assigned_to is ObjectId before comparing
                    if isinstance(task.get('assigned_to'), ObjectId) and task.get('assigned_to') == user_obj_id:
                        is_assigned = True
                        break
        except (bson_errors.InvalidId, TypeError):
             # print(f"Decorator Warning: Could not convert current_user.id '{current_user.id}' to ObjectId.")
             pass

        if not (is_admin or is_owner or is_assigned):
            # print(f"Access Denied: User {current_user.id}, Project {project_id}. is_admin:{is_admin}, is_owner:{is_owner}, is_assigned:{is_assigned}")
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function