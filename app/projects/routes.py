# pandora_pm/app/projects/routes.py
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from . import bp
from ..models import (
    create_project, get_project_by_id, get_projects_for_user,
    add_task_to_project, get_task_from_project, update_task_status_in_project,
    delete_task_from_project, delete_project,
    User, get_user_dict, update_task_in_project
)
# === Import admin_required decorator ===
from ..decorators import project_owner_required, project_access_required, admin_required
# === END Import ===
from datetime import datetime
from bson import ObjectId, errors as bson_errors

# --- Project Routes ---

@bp.route('/')
@login_required
def project_list():
    """Displays list of projects user has access to."""
    projects = get_projects_for_user(current_user.id)
    return render_template('projects/project_list.html', title='My Projects', projects=projects)

# === APPLY admin_required DECORATOR ===
@bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required # Only admins can create projects
def new_project():
# === END DECORATOR CHANGE ===
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')

        if not name:
            flash('Project name is required.', 'danger')
            return render_template('projects/project_form.html', title='New Project', project=None, name=name, description=description, due_date=due_date_str)
        else:
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    return render_template('projects/project_form.html', title='New Project', project=None, name=name, description=description, due_date=due_date_str)

            # Project owner is the admin creating it
            project_id = create_project(name, description, current_user.id, due_date=due_date)
            if project_id:
                flash('Project created successfully!', 'success')
                # Admins might want to be redirected to the project list or the new project
                return redirect(url_for('projects.project_detail', project_id=project_id))
            else:
                flash('Error creating project.', 'danger')
                return render_template('projects/project_form.html', title='New Project', project=None, name=name, description=description, due_date=due_date_str)

    # GET request
    return render_template('projects/project_form.html', title='New Project', project=None)


# Use project_access_required so assigned users can VIEW details
@bp.route('/<project_id>')
@login_required
@project_access_required
def project_detail(project_id):
    project = get_project_by_id(project_id)
    if not project:
         abort(404)

    tasks = sorted(project.get('tasks', []), key=lambda t: (t.get('due_date') is None, t.get('due_date'), t.get('created_at')))
    users_dict = get_user_dict()

    return render_template('projects/project_detail.html',
                           title=project.get('name', 'Project Details'),
                           project=project,
                           tasks=tasks,
                           users_dict=users_dict)

# Use project_access_required so assigned users can reach the edit page (to update status)
@bp.route('/<project_id>/edit', methods=['GET', 'POST'])
@login_required
@project_access_required # Allow access to page
def edit_project(project_id):
    project = get_project_by_id(project_id)
    if not project:
        abort(404)

    # Determine if the current user is the owner
    is_owner = str(project.get('owner_id')) == current_user.id

    if request.method == 'POST':
        # Get submitted data
        submitted_status = request.form.get('status')

        # --- Permission Check for Update ---
        if current_user.is_admin or is_owner:
            # Admins and Owners can update all fields
            submitted_name = request.form.get('name')
            submitted_description = request.form.get('description', '')
            submitted_due_date_str = request.form.get('due_date')

            if not submitted_name:
                flash('Project name is required for owners/admins.', 'danger')
                 # Re-render with error
                return render_template('projects/project_form.html', title='Edit Project', project=project, name=submitted_name, description=submitted_description, status=submitted_status, due_date=submitted_due_date_str)

            due_date = None
            if submitted_due_date_str:
                try:
                    due_date = datetime.strptime(submitted_due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    # Re-render with error
                    return render_template('projects/project_form.html', title='Edit Project', project=project, name=submitted_name, description=submitted_description, status=submitted_status, due_date=submitted_due_date_str)

            # Prepare full update payload for admin/owner
            update_data = {
                'name': submitted_name,
                'description': submitted_description,
                'status': submitted_status,
                'due_date': due_date,
                'updated_at': datetime.utcnow()
            }
        else:
            # Regular assigned users can ONLY update status
            update_data = {
                'status': submitted_status,
                'updated_at': datetime.utcnow()
            }
            flash('Permission granted to update status only.', 'info') # Optional feedback

        # --- Perform Update ---
        try:
            from ..extensions import mongo
            result = mongo.db.projects.update_one(
                {'_id': ObjectId(project_id)},
                {'$set': update_data}
            )
            # Check if matched and modified
            if result.matched_count:
                 if result.modified_count > 0:
                      flash('Project updated successfully!', 'success')
                 else:
                      # Check if only status was submitted by non-owner/admin and it didn't change
                      if not (current_user.is_admin or is_owner) and submitted_status == project.get('status'):
                         flash('No changes detected in project status.', 'info')
                      elif not (current_user.is_admin or is_owner):
                          # This case should ideally not happen if status was different
                          flash('Project status updated successfully!', 'success')
                      else:
                          flash('No changes detected in project details.', 'info')
            else:
                 flash('Project not found during update.', 'warning') # Should not happen

            return redirect(url_for('projects.project_detail', project_id=project_id))

        except bson_errors.InvalidId:
             abort(404) # Should not happen
        except Exception as e:
             flash(f'Error updating project: {e}', 'danger')
             # Re-render form, pre-filling with original project data might be safer on error
             due_date_val = project.get('due_date').strftime('%Y-%m-%d') if project.get('due_date') else ''
             return render_template('projects/project_form.html', title='Edit Project', project=project, name=project.get('name'), description=project.get('description'), status=project.get('status'), due_date=due_date_val)


    # --- GET Request ---
    # Pre-fill form with existing project data
    due_date_val = project.get('due_date').strftime('%Y-%m-%d') if project.get('due_date') else ''
    return render_template('projects/project_form.html',
                           title='Edit Project',
                           project=project, # Pass project object for checks in template
                           name=project.get('name'),
                           description=project.get('description'),
                           status=project.get('status'),
                           due_date=due_date_val)


# Only Admin or Owner should delete project
@bp.route('/<project_id>/delete', methods=['POST'])
@login_required
@project_owner_required # Keep this strict decorator
def delete_project_route(project_id):
     if delete_project(project_id):
         flash('Project deleted successfully.', 'success')
         return redirect(url_for('projects.project_list'))
     else:
         flash('Error deleting project.', 'danger')
         return redirect(url_for('projects.project_detail', project_id=project_id))


# --- Task Routes ---
# Decide who can add/edit/delete tasks. Keeping owner for now.

# Only Admin or Owner should add tasks
@bp.route('/<project_id>/tasks/new', methods=['GET', 'POST'])
@login_required
@project_owner_required # Keep this strict decorator
def new_task(project_id):
    # ... (logic remains the same) ...
    project = get_project_by_id(project_id)
    if not project: abort(404)
    users_list = User.get_all_users()
    if request.method == 'POST':
        # ... (form processing logic) ...
        name = request.form.get('name')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        assigned_to_user_id = request.form.get('assigned_to')
        form_data = {'name': name,'description': description,'due_date': due_date_str,'assigned_to_id': assigned_to_user_id}
        if not name:
            flash('Task name is required.', 'danger')
            return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None, **form_data)
        else:
            due_date = None
            if due_date_str:
                try: due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None, **form_data)
            task_id = add_task_to_project(project_id, name, description, current_user.id, due_date=due_date, assigned_to_id=assigned_to_user_id if assigned_to_user_id else None)
            if task_id:
                flash('Task added successfully!', 'success')
                return redirect(url_for('projects.project_detail', project_id=project_id))
            else:
                flash('Error adding task.', 'danger')
                return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None, **form_data)
    return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None)


# Only Admin or Owner should edit tasks
@bp.route('/<project_id>/tasks/<task_id>/edit', methods=['GET', 'POST'])
@login_required
@project_owner_required # Keep this strict decorator
def edit_task(project_id, task_id):
    # ... (logic remains the same) ...
    project = get_project_by_id(project_id)
    if not project: abort(404)
    task = get_task_from_project(project_id, task_id)
    if not task: abort(404)
    users_list = User.get_all_users()
    if request.method == 'POST':
        # ... (form processing logic) ...
        name = request.form.get('name')
        description = request.form.get('description', '')
        status = request.form.get('status')
        due_date_str = request.form.get('due_date')
        assigned_to_user_id = request.form.get('assigned_to')
        form_data = {'name': name,'description': description,'status': status,'due_date': due_date_str,'assigned_to_id': assigned_to_user_id}
        if not name:
            flash('Task name is required.', 'danger')
            return render_template('tasks/task_form.html', title='Edit Task', project=project, task=task, users=users_list, **form_data)
        due_date = None
        if due_date_str:
            try: due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                return render_template('tasks/task_form.html', title='Edit Task', project=project, task=task, users=users_list, **form_data)
        update_payload = {'name': name,'description': description,'status': status,'due_date': due_date,'assigned_to': assigned_to_user_id if assigned_to_user_id else None}
        if update_task_in_project(project_id, task_id, update_payload):
            flash('Task updated successfully!', 'success')
            return redirect(url_for('projects.project_detail', project_id=project_id, _anchor=f'task-{task_id}'))
        else:
            flash('Error updating task, or no changes detected.', 'danger')
            return render_template('tasks/task_form.html', title='Edit Task', project=project, task=task, users=users_list, **form_data)
    due_date_val = task.get('due_date').strftime('%Y-%m-%d') if task.get('due_date') else ''
    assigned_id_val = str(task.get('assigned_to')) if task.get('assigned_to') else ''
    return render_template('tasks/task_form.html', title='Edit Task', project=project, task=task, users=users_list, name=task.get('name'), description=task.get('description'), status=task.get('status'), due_date=due_date_val, assigned_to_id=assigned_id_val)


# Use project_access_required - allows owner, admin, or assigned user to update status
@bp.route('/<project_id>/tasks/<task_id>/update_status', methods=['POST'])
@login_required
@project_access_required
def update_task_status_route(project_id, task_id):
    # Add more specific permission check here if needed (e.g., only task assignee)
    new_status = request.form.get('status')
    allowed_statuses = ['To Do', 'In Progress', 'Done']
    if not new_status or new_status not in allowed_statuses:
         flash(f'Invalid status provided. Must be one of: {", ".join(allowed_statuses)}', 'warning')
    elif update_task_status_in_project(project_id, task_id, new_status):
        flash('Task status updated.', 'success')
    else:
        flash('Error updating task status.', 'danger')
    return redirect(url_for('projects.project_detail', project_id=project_id, _anchor=f'task-{task_id}'))


# Only Admin or Owner should delete tasks
@bp.route('/<project_id>/tasks/<task_id>/delete', methods=['POST'])
@login_required
@project_owner_required # Keep this strict decorator
def delete_task_route(project_id, task_id):
     if delete_task_from_project(project_id, task_id):
         flash('Task deleted successfully.', 'success')
     else:
         flash('Error deleting task.', 'danger')
     return redirect(url_for('projects.project_detail', project_id=project_id))