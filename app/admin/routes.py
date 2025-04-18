# pandora_pm/app/admin/routes.py
from flask import render_template, flash, redirect, url_for, request, abort
from flask_login import login_required, current_user
from . import bp
from ..models import User # Use User model helpers
from ..decorators import admin_required
from ..extensions import mongo # Direct DB access if needed
from bson import ObjectId, errors as bson_errors
from datetime import datetime

@bp.route('/users')
@login_required
@admin_required
def user_list():
    users = User.get_all_users()
    return render_template('admin/user_list.html', title='Manage Users', users=users)

@bp.route('/users/set_role/<user_id>', methods=['POST'])
@login_required
@admin_required
def set_user_role(user_id):
    new_role = request.form.get('role')
    target_user = User.get_by_id(user_id)

    if not target_user:
        flash('User not found.', 'danger'); return redirect(url_for('admin.user_list'))
    if target_user.id == current_user.id and new_role != 'admin':
        flash('Admins cannot remove their own admin role via the quick role change.', 'warning'); return redirect(url_for('admin.user_list'))
    if new_role not in ['admin', 'user']:
        flash('Invalid role specified.', 'danger'); return redirect(url_for('admin.user_list'))

    if User.set_role(user_id, new_role): flash(f"User '{target_user.username}' role updated successfully to {new_role}.", 'success')
    else: flash(f"Error updating role for user '{target_user.username}'.", 'danger')
    return redirect(url_for('admin.user_list'))

@bp.route('/users/edit/<user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    try:
        user_obj_id = ObjectId(user_id)
        user_data = mongo.db.users.find_one({'_id': user_obj_id})
    except (bson_errors.InvalidId, TypeError): abort(404)
    if not user_data: abort(404)

    user_to_edit = user_data

    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_email = request.form.get('email', '').strip()
        new_role = request.form.get('role') if request.form.get('role') else user_to_edit.get('role')

        errors = []
        if not new_username: errors.append('Username is required.')
        if not new_email: errors.append('Email is required.')
        if '@' not in new_email or '.' not in new_email: errors.append('Invalid email format.')
        if new_username != user_to_edit.get('username'):
            if mongo.db.users.find_one({'username': new_username, '_id': {'$ne': user_obj_id}}): errors.append('Username is already taken by another user.')
        if new_email != user_to_edit.get('email'):
             if mongo.db.users.find_one({'email': new_email, '_id': {'$ne': user_obj_id}}): errors.append('Email is already taken by another user.')
        if new_role not in ['admin', 'user']: errors.append('Invalid role selected.')
        is_editing_self = (str(current_user.id) == user_id)
        if is_editing_self and new_role != 'admin' and current_user.is_admin:
            flash('Admins cannot change their own role. Role change ignored.', 'warning'); new_role = 'admin'

        if errors:
            for error in errors: flash(error, 'danger')
            return render_template('admin/user_edit.html', title=f'Edit User {user_to_edit["username"]}', user_to_edit=user_to_edit)
        else:
            update_fields = {'username': new_username,'email': new_email,'role': new_role,'updated_at': datetime.utcnow()}
            try:
                result = mongo.db.users.update_one({'_id': user_obj_id},{'$set': update_fields})
                changes_made = any(update_fields[key] != user_to_edit.get(key) for key in ['username', 'email', 'role'])
                if result.matched_count and changes_made: flash(f"User '{new_username}' updated successfully.", 'success')
                elif result.matched_count: flash('No changes were detected.', 'info')
                else: flash('User not found during update.', 'danger')
                return redirect(url_for('admin.user_list'))
            except Exception as e:
                 flash(f'An error occurred while updating the user: {e}', 'danger')
                 return render_template('admin/user_edit.html', title=f'Edit User {user_to_edit["username"]}', user_to_edit=user_to_edit)

    return render_template('admin/user_edit.html', title=f'Edit User {user_to_edit["username"]}', user_to_edit=user_to_edit)

@bp.route('/users/delete/<user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger'); return redirect(url_for('admin.user_list'))
    try:
        user_obj_id = ObjectId(user_id)
        user_to_delete = mongo.db.users.find_one({'_id': user_obj_id})
        if not user_to_delete: flash('User not found.', 'danger'); return redirect(url_for('admin.user_list'))
        result = mongo.db.users.delete_one({'_id': user_obj_id})
        if result.deleted_count == 1: flash(f"User '{user_to_delete.get('username', 'Unknown')}' deleted successfully.", 'success')
        else: flash(f"Error deleting user '{user_to_delete.get('username', 'Unknown')}'.", 'danger')
    except (bson_errors.InvalidId, TypeError): flash('Invalid user ID format.', 'danger')
    except Exception as e: flash(f'An error occurred: {e}', 'danger'); # Log error e
    return redirect(url_for('admin.user_list'))