# pandora_pm/app/projects/routes.py
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from . import bp
from ..models import (
    create_project, get_project_by_id, get_projects_for_user,
    add_task_to_project, get_task_from_project, update_task_status_in_project,
    delete_task_from_project, delete_project # Import delete functions
)
from ..decorators import project_owner_required # Import decorator
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
        description = request.form.get('description', '') # Default to empty string
        due_date_str = request.form.get('due_date')

        if not name:
            flash('Project name is required.', 'danger')
        else:
            due_date = None
            if due_date_str:
                try:
                    # Combine date with start of day time for consistency if needed
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    # Re-render form with entered data
                    return render_template('projects/project_form.html', title='New Project', name=name, description=description, due_date=due_date_str)

            project_id = create_project(name, description, current_user.id, due_date=due_date)
            if project_id:
                flash('Project created successfully!', 'success')
                return redirect(url_for('projects.project_detail', project_id=project_id))
            else:
                flash('Error creating project.', 'danger')

    return render_template('projects/project_form.html', title='New Project', project=None) # Pass project=None for new

@bp.route('/<project_id>')
@login_required
@project_owner_required # Use decorator to check ownership/admin status
def project_detail(project_id):
    # Decorator already fetches and validates project_id and ownership
    project = get_project_by_id(project_id) # Fetch again or pass from decorator if modified
    if not project:
         abort(404) # Should not happen if decorator works, but safety check

    # Tasks are embedded in this example, sort them if needed
    tasks = sorted(project.get('tasks', []), key=lambda t: (t.get('due_date') is None, t.get('due_date'), t.get('created_at')))

    return render_template('projects/project_detail.html',
                           title=project.get('name', 'Project Details'),
                           project=project,
                           tasks=tasks)

@bp.route('/<project_id>/edit', methods=['GET', 'POST'])
@login_required
@project_owner_required
def edit_project(project_id):
    project = get_project_by_id(project_id) # Fetch project data
    if not project:
        abort(404)

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        status = request.form.get('status') # Add status field to form
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
                    # Re-render form with current data + error
                    return render_template('projects/project_form.html', title='Edit Project', project=project, name=name, description=description, status=status, due_date=due_date_str)

            # Update project in DB (create a model function for this)
            try:
                update_data = {
                    'name': name,
                    'description': description,
                    'status': status,
                    'due_date': due_date,
                    'updated_at': datetime.utcnow()
                 }
                # Remove keys with None values if you don't want to overwrite with null
                # update_data = {k: v for k, v in update_data.items() if v is not None}

                from ..extensions import mongo # Direct access or use model func
                result = mongo.db.projects.update_one(
                    {'_id': ObjectId(project_id)},
                    {'$set': update_data}
                )
                if result.matched_count:
                     flash('Project updated successfully!', 'success')
                else:
                     flash('Project not found or no changes made.', 'warning') # Should not happen due to decorator
                return redirect(url_for('projects.project_detail', project_id=project_id))

            except bson_errors.InvalidId:
                 abort(404)
            except Exception as e:
                 flash(f'Error updating project: {e}', 'danger')


    # Pre-fill form for GET request
    # Convert datetime back to string for date input
    due_date_val = project.get('due_date').strftime('%Y-%m-%d') if project.get('due_date') else ''
    return render_template('projects/project_form.html', title='Edit Project', project=project, name=project.get('name'), description=project.get('description'), status=project.get('status'), due_date=due_date_val)


@bp.route('/<project_id>/delete', methods=['POST'])
@login_required
@project_owner_required
def delete_project_route(project_id):
     # Add confirmation step in the template form
     if delete_project(project_id):
         flash('Project deleted successfully.', 'success')
         return redirect(url_for('projects.project_list'))
     else:
         flash('Error deleting project.', 'danger')
         return redirect(url_for('projects.project_detail', project_id=project_id))


# --- Task Routes ---

@bp.route('/<project_id>/tasks/new', methods=['GET', 'POST'])
@login_required
@project_owner_required # Only owner can add tasks in this simple setup
def new_task(project_id):
    project = get_project_by_id(project_id) # Needed for context in template
    if not project: abort(404)

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        # Add assigned_to field if implementing assignments

        if not name:
            flash('Task name is required.', 'danger')
        else:
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    return render_template('tasks/task_form.html', title='New Task', project=project, name=name, description=description, due_date=due_date_str)

            task_id = add_task_to_project(project_id, name, description, current_user.id, due_date=due_date)
            if task_id:
                flash('Task added successfully!', 'success')
                return redirect(url_for('projects.project_detail', project_id=project_id))
            else:
                flash('Error adding task. Project might not exist or database error.', 'danger')

    return render_template('tasks/task_form.html', title='New Task', project=project, task=None) # task=None for new

# Add Edit Task Route (similar to edit_project, needs a task_form.html)
# @bp.route('/<project_id>/tasks/<task_id>/edit', methods=['GET', 'POST'])
# @login_required
# @project_owner_required # Or check if assigned user
# def edit_task(project_id, task_id):
#     # ... fetch project, fetch task ...
#     # ... handle POST to update task in project document ...
#     # ... render task_form.html with existing data ...

@bp.route('/<project_id>/tasks/<task_id>/update_status', methods=['POST'])
@login_required
@project_owner_required # Or check if assigned user can update status
def update_task_status_route(project_id, task_id):
    new_status = request.form.get('status')
    # TODO: Validate status against allowed values ('To Do', 'In Progress', 'Done')
    if not new_status:
         flash('No status provided.', 'warning')
    elif update_task_status_in_project(project_id, task_id, new_status):
        flash('Task status updated.', 'success')
    else:
        flash('Error updating task status. Task or Project not found?', 'danger')

    return redirect(url_for('projects.project_detail', project_id=project_id))


@bp.route('/<project_id>/tasks/<task_id>/delete', methods=['POST'])
@login_required
@project_owner_required # Only owner can delete tasks in this setup
def delete_task_route(project_id, task_id):
     # Add confirmation in the template form if desired
     if delete_task_from_project(project_id, task_id):
         flash('Task deleted successfully.', 'success')
     else:
         flash('Error deleting task.', 'danger')
     return redirect(url_for('projects.project_detail', project_id=project_id))