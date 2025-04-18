# pandora_pm/app/decorators.py
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    """
    Decorator to ensure the current user is logged in and has the 'admin' role.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Redirect to login if not authenticated
            flash('You must be logged in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            # Abort with 403 Forbidden if not an admin
            flash('You do not have permission to access this resource (Admin Required).', 'danger')
            # Redirecting to dashboard might be friendlier than abort(403)
            return redirect(url_for('main.dashboard'))
            # Or use abort(403) for a hard stop:
            # abort(403)
        return f(*args, **kwargs)
    return decorated_function

# You could add other decorators, e.g., permission_required(permission)