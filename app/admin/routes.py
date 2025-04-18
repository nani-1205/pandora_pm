from flask import render_template, flash, redirect, url_for, request, abort
from flask_login import login_required
from bson import ObjectId
from . import bp
from ..models import User # Import User model helpers
from ..decorators import admin_required # Use the admin decorator

@bp.route('/users')
@admin_required # Protect this route
def user_list():
    """Displays a list of all users for admins."""
    try:
        users = User.get_all_users()
    except Exception as e:
        flash(f"Error fetching users: {e}", "danger")
        users = []
    return render_template('admin/user_list.html', title='Manage Users', users=users)

@bp.route('/users/set_role/<user_id>', methods=['POST'])
@admin_required # Protect this action
def set_user_role(user_id):
    """Sets the role of a user."""
    new_role = request.form.get('role')
    if not new_role or new_role not in ['admin', 'user']:
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('admin.user_list'))

    # Prevent admin from accidentally removing their own admin role if they are the only one
    target_user = User.get_by_id(user_id)
    if not target_user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.user_list'))

    if str(current_user.id) == user_id and new_role == 'user':
         # Check if they are the *only* admin left
         admin_count = User.get_collection().count_documents({'role': 'admin'})
         if admin_count <= 1:
              flash('Cannot remove the only administrator role.', 'danger')
              return redirect(url_for('admin.user_list'))

    # Proceed with role update
    success = User.update_role(user_id, new_role)
    if success:
        flash(f"User '{target_user.username}' role updated successfully to '{new_role}'.", 'success')
    else:
        flash(f'Error updating role for user {target_user.username}.', 'danger')

    return redirect(url_for('admin.user_list'))

# Add routes for deleting users (with confirmation!), viewing user details, etc.
# Be very careful with delete operations!
# @bp.route('/users/delete/<user_id>', methods=['POST'])
# @admin_required
# def delete_user(user_id):
#     # Add checks: cannot delete self, confirmation step?
#     # ... delete logic ...
#     flash('User deleted.', 'success')
#     return redirect(url_for('admin.user_list'))