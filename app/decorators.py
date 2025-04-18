# app/decorators.py
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required for this page.', 'danger')
            return redirect(url_for('dashboard')) # Redirect non-admins
        return f(*args, **kwargs)
    return decorated_function