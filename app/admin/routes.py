# pandora_pm/app/admin/routes.py
from flask import render_template, flash, redirect, url_for, request, abort
from flask_login import login_required, current_user
from . import bp
from ..models import User # Import User model helpers
from ..decorators import admin_required
from ..extensions import mongo # Direct DB access
from bson import ObjectId, errors as bson_errors
from datetime import datetime # Needed for updated_at timestamp

@bp.route('/users')
@login_required
@admin_required
def user_list():
    users = User.get_all_users()
    return render_template('admin/user_list.html', title='Manage Users', users=users)

# Route to change role quickly from list view - requires POST for security
@bp.route('/users/set_role/<user_id>', methods=['POST'])
@login_required
@admin_required
def set_user_role(user_id):
    new_role = request.form.get('role')
    target_user = User.get_by_id(user_id) # Returns User object wrapper

    if not target_user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.user_list'))

    # Prevent admin from accidentally removing their own admin role via this specific form
    if target_user.id == current_user.id and new_role != 'admin':
        flash('Admins cannot remove their own admin role via the quick role change.', 'warning')
        return redirect(url_for('admin.user_list'))

    if new_role not in ['admin', 'user']:
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('admin.user_list'))

    # Use the static method from the User model
    if User.set_role(user_id, new_role):
        flash(f"User '{target_user.username}' role updated successfully to {new_role}.", 'success')
    else:
        flash(f"Error updating role for user '{target_user.username}'.", 'danger')

    return redirect(url_for('admin.user_list'))

# --- NEW: Route to display and handle the user edit form ---
@bp.route('/users/edit/<user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    try:
        user_obj_id = ObjectId(user_id)
        # Fetch raw data for the form, could also use User.get_by_id(user_id).data
        user_data = mongo.db.users.find_one({'_id': user_obj_id})
    except (bson_errors.InvalidId, TypeError):
        abort(404) # Invalid ID format

    if not user_data:
        abort(404) # User not found

    # Pass the raw dict to the template for easy pre-filling
    user_to_edit = user_data

    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_email = request.form.get('email', '').strip()
        # Role might be disabled in the form if editing self, check if submitted
        new_role = request.form.get('role') if request.form.get('role') else user_to_edit.get('role')

        # --- Validation ---
        errors = []
        if not new_username: errors.append('Username is required.')
        if not new_email: errors.append('Email is required.')
        # Basic email format check (use library for robust check)
        if '@' not in new_email or '.' not in new_email:
             errors.append('Invalid email format.')

        # Check if username or email is already taken by ANOTHER user
        if new_username != user_to_edit.get('username'):
            existing_user_username = mongo.db.users.find_one({'username': new_username, '_id': {'$ne': user_obj_id}})
            if existing_user_username:
                errors.append('Username is already taken by another user.')
        if new_email != user_to_edit.get('email'):
            existing_user_email = mongo.db.users.find_one({'email': new_email, '_id': {'$ne': user_obj_id}})
            if existing_user_email:
                 errors.append('Email is already taken by another user.')

        # Validate role (but respect disabled field if editing self)
        if new_role not in ['admin', 'user']:
            errors.append('Invalid role selected.')
        # Double check self-role change attempt (form should disable it, but belt-and-suspenders)
        is_editing_self = (str(current_user.id) == user_id)
        if is_editing_self and new_role != 'admin' and current_user.is_admin:
            flash('Admins cannot change their own role. Role change ignored.', 'warning')
            new_role = 'admin' # Ensure role remains admin

        if errors:
            for error in errors:
                flash(error, 'danger')
            # Re-render form with submitted data (which is in request.form) and errors
            return render_template('admin/user_edit.html', title=f'Edit User {user_to_edit["username"]}', user_to_edit=user_to_edit)
        else:
            # --- Update Database ---
            update_fields = {
                'username': new_username,
                'email': new_email,
                'role': new_role, # Role is validated above
                'updated_at': datetime.utcnow() # Keep track of updates
            }

            try:
                result = mongo.db.users.update_one(
                    {'_id': user_obj_id},
                    {'$set': update_fields}
                )
                # Check if any document was actually modified
                changes_made = any(update_fields[key] != user_to_edit.get(key) for key in ['username', 'email', 'role'])

                if result.matched_count and changes_made:
                     flash(f"User '{new_username}' updated successfully.", 'success')
                elif result.matched_count:
                     flash('No changes were detected.', 'info')
                else:
                     # This shouldn't happen if we found the user initially
                     flash('User not found during update.', 'danger')

                return redirect(url_for('admin.user_list'))
            except Exception as e:
                 flash(f'An error occurred while updating the user: {e}', 'danger')
                 # Log the error e
                 return render_template('admin/user_edit.html', title=f'Edit User {user_to_edit["username"]}', user_to_edit=user_to_edit)

    # --- GET Request ---
    # Render the form, pre-filled with user_to_edit data
    return render_template('admin/user_edit.html', title=f'Edit User {user_to_edit["username"]}', user_to_edit=user_to_edit)


# --- NEW: Route to delete users ---
@bp.route('/users/delete/<user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    # Critical check: Do not allow admin to delete themselves!
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.user_list'))

    try:
        user_obj_id = ObjectId(user_id)
        user_to_delete = mongo.db.users.find_one({'_id': user_obj_id})

        if not user_to_delete:
            flash('User not found.', 'danger')
            return redirect(url_for('admin.user_list'))

        # Perform the delete operation
        result = mongo.db.users.delete_one({'_id': user_obj_id})

        if result.deleted_count == 1:
            flash(f"User '{user_to_delete.get('username', 'Unknown')}' deleted successfully.", 'success')
            # Consider what to do with projects/tasks owned by the deleted user
            # Option 1: Delete them (cascade delete - complex)
            # Option 2: Reassign them to another admin/user
            # Option 3: Leave them orphaned (might cause issues)
            # print(f"TODO: Handle projects/tasks owned by deleted user {user_id}")
        else:
            flash(f"Error deleting user '{user_to_delete.get('username', 'Unknown')}'.", 'danger')

    except (bson_errors.InvalidId, TypeError):
        flash('Invalid user ID format.', 'danger')
    except Exception as e:
        flash(f'An error occurred: {e}', 'danger')
        # Log error e

    return redirect(url_for('admin.user_list'))