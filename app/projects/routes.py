# pandora_pm/app/projects/routes.py
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from . import bp
from ..models import (
    create_project, get_project_by_id, get_projects_for_user,
    add_task_to_project, get_task_from_project, update_task_status_in_project,
    delete_task_from_project, delete_project,
    # --- Add User model and helper ---
    User,
    get_user_dict,
    update_task_in_project # Import if implementing edit task
    # --- End Add ---
)
from ..decorators import project_owner_required
from datetime import datetime
from bson import ObjectId, errors as bson_errors

# --- Project Routes ---

@bp.route('/')
@login_required
def project_list():
    """Displays list of projects for the current user."""
    projects = get_projects_for_user(current_user.id)
    return render_template('projects/project_list.html', title='My Projects', projects=projects)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_project():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')

        if not name:
            flash('Project name is required.', 'danger')
        else:
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    return render_template('projects/project_form.html', title='New Project', name=name, description=description, due_date=due_date_str)

            project_id = create_project(name, description, current_user.id, due_date=due_date)
            if project_id:
                flash('Project created successfully!', 'success')
                return redirect(url_for('projects.project_detail', project_id=project_id))
            else:
                flash('Error creating project.', 'danger')

    return render_template('projects/project_form.html', title='New Project', project=None)

@bp.route('/<project_id>')
@login_required
@project_owner_required
def project_detail(project_id):
    project = get_project_by_id(project_id)
    if not project:
         abort(404)

    # Sort tasks by due date (None last), then creation date
    tasks = sorted(project.get('tasks', []), key=lambda t: (t.get('due_date') is None, t.get('due_date'), t.get('created_at')))

    # --- Fetch user dictionary for display ---
    users_dict = get_user_dict()
    # --- End Fetch ---

    return render_template('projects/project_detail.html',
                           title=project.get('name', 'Project Details'),
                           project=project,
                           tasks=tasks,
                           users_dict=users_dict) # Pass the dictionary

@bp.route('/<project_id>/edit', methods=['GET', 'POST'])
@login_required
@project_owner_required
def edit_project(project_id):
    project = get_project_by_id(project_id)
    if not project:
        abort(404)

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        status = request.form.get('status')
        due_date_str = request.form.get('due_date')

        if not name:
            flash('Project name is required.', 'danger')
        else:
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    return render_template('projects/project_form.html', title='Edit Project', project=project, name=name, description=description, status=status, due_date=due_date_str)

            try:
                update_data = {
                    'name': name,
                    'description': description,
                    'status': status,
                    'due_date': due_date,
                    'updated_at': datetime.utcnow()
                 }
                from ..extensions import mongo
                result = mongo.db.projects.update_one(
                    {'_id': ObjectId(project_id)},
                    {'$set': update_data}
                )
                if result.matched_count:
                     # Check if anything actually changed before flashing success
                     if result.modified_count > 0:
                          flash('Project updated successfully!', 'success')
                     else:
                          flash('No changes detected for the project.', 'info')
                else:
                     flash('Project not found during update.', 'warning')
                return redirect(url_for('projects.project_detail', project_id=project_id))

            except bson_errors.InvalidId:
                 abort(404)
            except Exception as e:
                 flash(f'Error updating project: {e}', 'danger')

    due_date_val = project.get('due_date').strftime('%Y-%m-%d') if project.get('due_date') else ''
    return render_template('projects/project_form.html', title='Edit Project', project=project, name=project.get('name'), description=project.get('description'), status=project.get('status'), due_date=due_date_val)


@bp.route('/<project_id>/delete', methods=['POST'])
@login_required
@project_owner_required
def delete_project_route(project_id):
     if delete_project(project_id):
         flash('Project deleted successfully.', 'success')
         return redirect(url_for('projects.project_list'))
     else:
         flash('Error deleting project.', 'danger')
         return redirect(url_for('projects.project_detail', project_id=project_id))


# --- Task Routes ---

@bp.route('/<project_id>/tasks/new', methods=['GET', 'POST'])
@login_required
@project_owner_required # Or adjust access control
def new_task(project_id):
    project = get_project_by_id(project_id)
    if not project: abort(404)

    # Fetch users for the dropdown
    users_list = User.get_all_users()

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        # Get assigned_to ID from form
        assigned_to_user_id = request.form.get('assigned_to') # Will be string ID or ""

        # Keep track of submitted values for re-rendering form on error
        form_data = {
            'name': name,
            'description': description,
            'due_date': due_date_str,
            'assigned_to_id': assigned_to_user_id
        }

        if not name:
            flash('Task name is required.', 'danger')
            # Re-render form with existing data and users list
            return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None, **form_data)

        else:
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    # Re-render form with existing data and users list
                    return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None, **form_data)

            # Pass assigned_to_user_id to model function
            task_id = add_task_to_project(
                project_id, name, description, current_user.id,
                due_date=due_date,
                # Pass ID string directly, model function handles ObjectId conversion or None
                assigned_to_id=assigned_to_user_id if assigned_to_user_id else None
            )

            if task_id:
                flash('Task added successfully!', 'success')
                return redirect(url_for('projects.project_detail', project_id=project_id))
            else:
                flash('Error adding task. Please check input or contact support.', 'danger')
                # Re-render form with existing data and users list
                return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None, **form_data)

    # GET Request: Pass users_list to the template
    return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None)


# Example: Edit Task Route (add more robust error handling)
@bp.route('/<project_id>/tasks/<task_id>/edit', methods=['GET', 'POST'])
@login_required
@project_owner_required # Or check if user is assignee
def edit_task(project_id, task_id):
    project = get_project_by_id(project_id)
    if not project: abort(404)
    task = get_task_from_project(project_id, task_id)
    if not task: abort(404)

    users_list = User.get_all_users()

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        status = request.form.get('status') # Get status from form
        due_date_str = request.form.get('due_date')
        assigned_to_user_id = request.form.get('assigned_to')

        form_data = {
            'name': name,
            'description': description,
            'status': status,
            'due_date': due_date_str,
            'assigned_to_id': assigned_to_user_id
        }

        if not name:
            flash('Task name is required.', 'danger')
            return render_template('tasks/task_form.html', title='Edit Task', project=project, task=task, users=users_list, **form_data)

        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                return render_template('tasks/task_form.html', title='Edit Task', project=project, task=task, users=users_list, **form_data)

        update_payload = {
            'name': name,
            'description': description,
            'status': status, # Include status in update
            'due_date': due_date,
            'assigned_to': assigned_to_user_id if assigned_to_user_id else None
        }

        if update_task_in_project(project_id, task_id, update_payload):
            flash('Task updated successfully!', 'success')
            return redirect(url_for('projects.project_detail', project_id=project_id))
        else:
            flash('Error updating task.', 'danger')
            # Re-render with submitted data might be needed if update_task fails
            return render_template('tasks/task_form.html', title='Edit Task', project=project, task=task, users=users_list, **form_data)


    # GET Request: Populate form with existing task data
    due_date_val = task.get('due_date').strftime('%Y-%m-%d') if task.get('due_date') else ''
    return render_template('tasks/task_form.html',
                           title='Edit Task',
                           project=project,
                           task=task,
                           users=users_list,
                           name=task.get('name'),
                           description=task.get('description'),
                           status=task.get('status'),
                           due_date=due_date_val,
                           assigned_to_id=str(task.get('assigned_to')) if task.get('assigned_to') else '')


@bp.route('/<project_id>/tasks/<task_id>/update_status', methods=['POST'])
@login_required
# Allow owner or assigned user to update status (more complex check needed if assignees != owner)
@project_owner_required # Simplistic check for now
def update_task_status_route(project_id, task_id):
    new_status = request.form.get('status')
    allowed_statuses = ['To Do', 'In Progress', 'Done'] # Define allowed statuses
    if not new_status or new_status not in allowed_statuses:
         flash(f'Invalid status provided. Must be one of: {", ".join(allowed_statuses)}', 'warning')
    elif update_task_status_in_project(project_id, task_id, new_status):
        flash('Task status updated.', 'success')
    else:
        flash('Error updating task status. Task or Project not found, or database error.', 'danger')

    # Redirect back to the project detail page, potentially anchoring to the task
    return redirect(url_for('projects.project_detail', project_id=project_id, _anchor=f'task-{task_id}'))


@bp.route('/<project_id>/tasks/<task_id>/delete', methods=['POST'])
@login_required
@project_owner_required # Only owner can delete tasks in this setup
def delete_task_route(project_id, task_id):
     if delete_task_from_project(project_id, task_id):
         flash('Task deleted successfully.', 'success')
     else:
         flash('Error deleting task.', 'danger')
     return redirect(url_for('projects.project_detail', project_id=project_id))