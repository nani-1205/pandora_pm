from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime
from . import bp
from ..models import (
    create_project, get_project_by_id, get_projects_for_user, User,
    add_task_to_project, get_task_from_project, update_task_status_in_project,
    delete_project_by_id, delete_task_from_project # Import new delete helpers
)
from ..decorators import admin_required # Maybe needed for some project actions

# --- Helper Function ---
def parse_date(date_string):
    """Safely parses YYYY-MM-DD string to datetime object."""
    if not date_string:
        return None
    try:
        # Return datetime object (time part will be 00:00:00)
        return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        return None # Indicate parsing failed

def check_project_permission(project_id, check_admin=True):
    """
    Checks if the current user owns the project or is an admin.
    Returns the project document if permission granted, otherwise aborts.
    """
    project = get_project_by_id(project_id)
    if not project:
        abort(404, description="Project not found")

    is_owner = str(project.get('owner_id')) == current_user.id
    is_allowed_admin = check_admin and current_user.is_admin

    # TODO: Add check for project members later if that feature is added
    # is_member = ObjectId(current_user.id) in project.get('members', [])

    if not is_owner and not is_allowed_admin: # Add 'and not is_member' later
        abort(403, description="You don't have permission to access this project.")

    return project # Return the project if access is allowed


# --- Project Routes ---

@bp.route('/')
@login_required
def project_list():
    """Displays list of projects owned by the current user."""
    projects = get_projects_for_user(current_user.id)
    return render_template('projects/project_list.html', title='My Projects', projects=projects)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_project():
    """Handles creation of a new project."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')

        if not name:
            flash('Project name is required.', 'danger')
        else:
            due_date = parse_date(due_date_str)
            if due_date_str and due_date is None: # Check if date was provided but invalid
                flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
            else:
                # Create the project
                project_id = create_project(name, description, current_user.id, due_date=due_date)
                if project_id:
                    flash(f'Project "{name}" created successfully!', 'success')
                    return redirect(url_for('projects.project_detail', project_id=str(project_id)))
                else:
                    flash('Error creating project. Please try again.', 'danger')

    # For GET request or if POST fails validation
    return render_template('projects/project_form.html', title='Create New Project', project=None) # Pass project=None for creation form


@bp.route('/<project_id>')
@login_required
def project_detail(project_id):
    """Displays details of a specific project and its tasks."""
    project = check_project_permission(project_id) # Checks permission and gets project

    # Sort tasks, e.g., by creation date or status
    tasks = sorted(project.get('tasks', []), key=lambda t: t.get('created_at', datetime.min))

    # Prepare data for assigning users (if implementing task assignment UI)
    # users = User.get_all_users() # Potentially filter users later

    return render_template('projects/project_detail.html',
                           title=project['name'],
                           project=project,
                           tasks=tasks
                           # users=users
                          )

@bp.route('/<project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = check_project_permission(project_id) # Only owner/admin can edit

    if request.method == 'POST':
        # --- Update logic ---
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        status = request.form.get('status', project.get('status')) # Keep old status if not provided
        due_date_str = request.form.get('due_date')

        if not name:
            flash('Project name cannot be empty.', 'danger')
        else:
             due_date = parse_date(due_date_str) if due_date_str else project.get('due_date') # Keep old date if empty string
             if due_date_str and due_date is None:
                flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
             else:
                # Update the project document in MongoDB
                update_data = {
                    'name': name,
                    'description': description,
                    'status': status,
                    'due_date': due_date,
                    'last_updated': datetime.utcnow()
                }
                result = mongo.db.projects.update_one(
                     {'_id': ObjectId(project_id)},
                     {'$set': update_data}
                )
                if result.modified_count > 0:
                    flash(f'Project "{name}" updated successfully!', 'success')
                else:
                     flash('No changes detected or error occurred.', 'info') # Could be no change or error
                return redirect(url_for('projects.project_detail', project_id=project_id))

    # --- GET request: Populate form with existing data ---
    # Format date for HTML input type="date"
    if project.get('due_date') and isinstance(project.get('due_date'), datetime):
         project['due_date_str'] = project['due_date'].strftime('%Y-%m-%d')
    else:
         project['due_date_str'] = ''

    # Define possible statuses (could be moved to config or a helper)
    possible_statuses = ["Not Started", "In Progress", "Completed", "On Hold", "Cancelled"]

    return render_template('projects/project_form.html',
                           title=f"Edit Project: {project['name']}",
                           project=project,
                           possible_statuses=possible_statuses)

@bp.route('/<project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = check_project_permission(project_id) # Only owner/admin can delete

    # Optional: Add extra confirmation step here if desired

    success = delete_project_by_id(project_id)
    if success:
        flash(f'Project "{project["name"]}" and its tasks have been deleted.', 'success')
        return redirect(url_for('projects.project_list'))
    else:
        flash('Error deleting project.', 'danger')
        return redirect(url_for('projects.project_detail', project_id=project_id))


# --- Task Routes ---

@bp.route('/<project_id>/tasks/new', methods=['GET', 'POST'])
@login_required
def new_task(project_id):
    """Handles adding a new task to a project."""
    project = check_project_permission(project_id) # Check project access first

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')
        # assigned_to_id = request.form.get('assigned_to') # Get assignee if form has it

        if not name:
            flash('Task name is required.', 'danger')
        else:
             due_date = parse_date(due_date_str)
             if due_date_str and due_date is None:
                 flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
             else:
                 # Add task to project's embedded list
                 task_id = add_task_to_project(
                     project_id,
                     name,
                     description,
                     current_user.id, # Created by current user
                     due_date=due_date
                     # assigned_to_id=assigned_to_id # Pass assignee if collected
                 )
                 if task_id:
                     flash('Task added successfully!', 'success')
                     return redirect(url_for('projects.project_detail', project_id=project_id))
                 else:
                     flash('Error adding task.', 'danger')

    # For GET request or if POST fails validation
    # users = User.get_all_users() # For assignment dropdown
    return render_template('tasks/task_form.html',
                            title='Add New Task',
                            project=project,
                            task=None # Indicate creation mode
                            # users=users
                           )

@bp.route('/<project_id>/tasks/<task_id>/update_status', methods=['POST'])
@login_required
def update_task_status_route(project_id, task_id):
    """Updates the status of a specific task via POST request."""
    project = check_project_permission(project_id) # Checks project permission

    new_status = request.form.get('status')
    # Validate status if needed (e.g., must be one of allowed values)
    allowed_statuses = ["To Do", "In Progress", "Done", "Blocked", "Review"]
    if not new_status or new_status not in allowed_statuses:
        flash('Invalid status provided.', 'warning')
        return redirect(url_for('projects.project_detail', project_id=project_id))

    # Check permission to update task (e.g., owner, assignee, admin)
    # task = get_task_from_project(project_id, task_id) # Fetch task if needed for assignee check
    # if not task: abort(404)
    # can_update = (str(project.get('owner_id')) == current_user.id or
    #               (task.get('assigned_to') and str(task.get('assigned_to')) == current_user.id) or
    #               current_user.is_admin)
    # if not can_update: abort(403)
    # Simple check: Only project owner/admin can update for now
    if str(project.get('owner_id')) != current_user.id and not current_user.is_admin:
        abort(403, description="You don't have permission to update this task.")

    success = update_task_status_in_project(project_id, task_id, new_status)
    if success:
        flash(f'Task status updated to "{new_status}".', 'success')
    else:
        flash('Error updating task status or task not found.', 'danger')

    return redirect(url_for('projects.project_detail', project_id=project_id))


@bp.route('/<project_id>/tasks/<task_id>/delete', methods=['POST'])
@login_required
def delete_task(project_id, task_id):
    project = check_project_permission(project_id) # Check project access

    # Add permission check if needed (e.g., only creator or project owner can delete)
    # task = get_task_from_project(project_id, task_id)
    # if not task: abort(404)
    # if str(task.get('created_by')) != current_user.id and str(project.get('owner_id')) != current_user.id:
    #     abort(403)

    success = delete_task_from_project(project_id, task_id)
    if success:
        flash('Task deleted successfully.', 'success')
    else:
        flash('Error deleting task or task not found.', 'danger')

    return redirect(url_for('projects.project_detail', project_id=project_id))


# Add routes for editing task details (similar to edit_project, rendering task_form.html)
# @bp.route('/<project_id>/tasks/<task_id>/edit', methods=['GET', 'POST'])
# @login_required
# def edit_task(project_id, task_id):
#     project = check_project_permission(project_id)
#     task = get_task_from_project(project_id, task_id)
#     if not task: abort(404)
#     # Add permission check for editing task
#
#     if request.method == 'POST':
#         # ... update logic using MongoDB update on the specific task element ...
#         # Use positional operator '$' or update the whole tasks array if simpler
#         flash('Task updated!', 'success')
#         return redirect(url_for('projects.project_detail', project_id=project_id))
#
#     # Prepare data for GET request
#     # users = User.get_all_users()
#     # if task.get('due_date') and isinstance(task.get('due_date'), datetime):
#     #      task['due_date_str'] = task['due_date'].strftime('%Y-%m-%d')
#
#     return render_template('tasks/task_form.html',
#                             title=f"Edit Task: {task['name']}",
#                             project=project,
#                             task=task # Pass existing task data
#                             # users=users
#                            )