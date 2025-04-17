# pandora_pm/app/decorators.py
from functools import wraps
from flask import abort, redirect, url_for, request, flash # Added imports for potential redirect
from flask_login import current_user
# --- Import necessary functions/objects ---
from .models import get_project_by_id
from bson import ObjectId, errors as bson_errors
# --- End Import ---

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ensure user is authenticated before checking admin status
        if not current_user.is_authenticated:
             flash('Please log in to access this page.', 'info')
             return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function

# Keep this decorator for actions only the owner should perform (Edit/Delete Project)
def project_owner_required(f):
     @wraps(f)
     def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login', next=request.url))

        project_id = kwargs.get('project_id')
        if not project_id: abort(500) # Internal error if project_id missing

        project = get_project_by_id(project_id)
        if not project: abort(404)

        # Allow access ONLY if user is admin OR owns the project
        if not current_user.is_admin and str(project.get('owner_id')) != current_user.id:
             abort(403)

        # Optional: Add project object to kwargs if view function needs it
        # kwargs['project'] = project
        return f(*args, **kwargs)
     return decorated_function

# --- ACCESS DECORATOR ---
def project_access_required(f):
    """Allows access if user is admin, owner, or assigned to any task in the project."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login', next=request.url)) # Redirect is often better

        project_id = kwargs.get('project_id')
        if not project_id: abort(500) # Internal error

        project = get_project_by_id(project_id)
        if not project: abort(404) # Project not found

        # Check conditions for access
        is_owner = str(project.get('owner_id')) == current_user.id
        is_admin = current_user.is_admin

        # Check if user is assigned to any task
        is_assigned = False
        try:
            # Ensure current_user.id can be converted to ObjectId
            user_obj_id = ObjectId(current_user.id)
            tasks = project.get('tasks', [])
            if tasks: # Only check if there are tasks
                for task in tasks:
                    # Safe check if assigned_to is None or not ObjectId
                    if isinstance(task.get('assigned_to'), ObjectId) and task.get('assigned_to') == user_obj_id:
                        is_assigned = True
                        break # Found one assignment, no need to check further
        except (bson_errors.InvalidId, TypeError):
             # Handle potential error converting current_user.id, though unlikely
             print(f"Decorator Warning: Could not convert current_user.id '{current_user.id}' to ObjectId.")
             pass # Treat as not assigned if conversion fails

        # Grant access if admin OR owner OR assigned
        if not (is_admin or is_owner or is_assigned):
            print(f"Access Denied: User {current_user.id}, Project {project_id}. is_admin:{is_admin}, is_owner:{is_owner}, is_assigned:{is_assigned}")
            abort(403) # Forbidden

        # Optional: Pass project to view function
        # kwargs['project'] = project
        return f(*args, **kwargs)
    return decorated_function
# --- END ACCESS DECORATOR ---