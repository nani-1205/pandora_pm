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
from ..decorators import project_owner_required, project_access_required, admin_required
from datetime import datetime
from bson import ObjectId, errors as bson_errors

# --- Project Routes ---

@bp.route('/')
@login_required
def project_list():
    # print(f"\n--- projects.project_list: ENTERING ROUTE ---") # Debug
    current_user_id = current_user.id
    # print(f"--- projects.project_list: current_user.id = '{current_user_id}', type = {type(current_user_id)} ---") # Debug
    projects = get_projects_for_user(current_user_id)
    # print(f"--- projects.project_list: EXITING ROUTE (Rendering template with {len(projects)} projects) ---") # Debug
    return render_template('projects/project_list.html', title='My Projects', projects=projects)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required # Only admins create
def new_project():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        form_data = {'name': name, 'description': description, 'due_date': due_date_str}
        if not name:
            flash('Project name is required.', 'danger')
            return render_template('projects/project_form.html', title='New Project', project=None, **form_data)
        else:
            due_date = None
            if due_date_str:
                try: due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    return render_template('projects/project_form.html', title='New Project', project=None, **form_data)
            project_id = create_project(name, description, current_user.id, due_date=due_date)
            if project_id:
                flash('Project created successfully!', 'success')
                return redirect(url_for('projects.project_detail', project_id=project_id))
            else:
                flash('Error creating project.', 'danger')
                return render_template('projects/project_form.html', title='New Project', project=None, **form_data)
    return render_template('projects/project_form.html', title='New Project', project=None)


@bp.route('/<project_id>')
@login_required
@project_access_required # Allow view access
def project_detail(project_id):
    project = get_project_by_id(project_id)
    if not project: abort(404)
    tasks = sorted(project.get('tasks', []), key=lambda t: (t.get('due_date') is None, t.get('due_date'), t.get('created_at')))
    users_dict = get_user_dict()
    return render_template('projects/project_detail.html', title=project.get('name', 'Project Details'), project=project, tasks=tasks, users_dict=users_dict)


@bp.route('/<project_id>/edit', methods=['GET', 'POST'])
@login_required
@project_access_required # Allow access to edit page
def edit_project(project_id):
    project = get_project_by_id(project_id)
    if not project: abort(404)
    is_owner = str(project.get('owner_id')) == current_user.id

    if request.method == 'POST':
        submitted_status = request.form.get('status')
        submitted_name = request.form.get('name')
        submitted_description = request.form.get('description', '')
        submitted_due_date_str = request.form.get('due_date')
        form_data = {'name': submitted_name, 'description': submitted_description, 'status': submitted_status, 'due_date': submitted_due_date_str}

        if current_user.is_admin or is_owner:
            if not submitted_name:
                flash('Project name is required for owners/admins.', 'danger')
                return render_template('projects/project_form.html', title='Edit Project', project=project, **form_data)
            due_date = None
            if submitted_due_date_str:
                try: due_date = datetime.strptime(submitted_due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    return render_template('projects/project_form.html', title='Edit Project', project=project, **form_data)
            update_data = { 'name': submitted_name, 'description': submitted_description, 'status': submitted_status, 'due_date': due_date, 'updated_at': datetime.utcnow() }
        else: # Assigned users only update status
            update_data = { 'status': submitted_status, 'updated_at': datetime.utcnow() }

        try:
            from ..extensions import mongo
            result = mongo.db.projects.update_one( {'_id': ObjectId(project_id)}, {'$set': update_data} )
            if result.matched_count:
                 if result.modified_count > 0: flash('Project updated successfully!', 'success')
                 else: flash('No changes detected in project details.', 'info')
            else: flash('Project not found during update.', 'warning')
            return redirect(url_for('projects.project_detail', project_id=project_id))
        except bson_errors.InvalidId: abort(404)
        except Exception as e:
             flash(f'Error updating project: {e}', 'danger')
             return render_template('projects/project_form.html', title='Edit Project', project=project, **form_data)

    due_date_val = project.get('due_date').strftime('%Y-%m-%d') if project.get('due_date') else ''
    return render_template('projects/project_form.html', title='Edit Project', project=project, name=project.get('name'), description=project.get('description'), status=project.get('status'), due_date=due_date_val)


@bp.route('/<project_id>/delete', methods=['POST'])
@login_required
@project_owner_required # Only owner/admin
def delete_project_route(project_id):
     if delete_project(project_id): flash('Project deleted successfully.', 'success'); return redirect(url_for('projects.project_list'))
     else: flash('Error deleting project.', 'danger'); return redirect(url_for('projects.project_detail', project_id=project_id))


# --- Task Routes ---

@bp.route('/<project_id>/tasks/new', methods=['GET', 'POST'])
@login_required
@project_owner_required # Only owner/admin adds tasks
def new_task(project_id):
    # print(f"\n--- projects.new_task: ENTERING ROUTE for project_id: {project_id}, Method: {request.method} ---") # Debug
    project = get_project_by_id(project_id)
    if not project: print(f"--- projects.new_task: ERROR - Project not found ---"); abort(404)
    users_list = User.get_all_users()
    # print(f"--- projects.new_task: Fetched {len(users_list)} users ---") # Debug

    if request.method == 'POST':
        # print("--- projects.new_task: Processing POST request ---") # Debug
        name = request.form.get('name')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date')
        assigned_to_user_id = request.form.get('assigned_to')
        # print(f"--- projects.new_task POST Data: name='{name}', ..., assigned_to='{assigned_to_user_id}' ---") # Debug
        form_data = { 'name': name, 'description': description, 'due_date': due_date_str, 'assigned_to_id': assigned_to_user_id }

        if not name:
            flash('Task name is required.', 'danger'); # print("--- projects.new_task: ERROR - Task name missing ---") # Debug
            return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None, **form_data)
        else:
            due_date = None
            if due_date_str:
                try: due_date = datetime.strptime(due_date_str, '%Y-%m-%d'); # print(f"--- projects.new_task: Parsed due_date: {due_date} ---") # Debug
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger'); # print(f"--- projects.new_task: ERROR - Invalid date format ---") # Debug
                    return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None, **form_data)

            creator_id = current_user.id
            assignee_id_to_pass = assigned_to_user_id if assigned_to_user_id else None
            # print(f"--- projects.new_task: Calling add_task_to_project with: assigned_to_id='{assignee_id_to_pass}' ---") # Debug
            task_id = add_task_to_project(project_id, name, description, creator_id, due_date=due_date, assigned_to_id=assignee_id_to_pass)
            # print(f"--- projects.new_task: add_task_to_project returned: {task_id} ---") # Debug

            if task_id:
                flash('Task added successfully!', 'success'); # print("--- projects.new_task: SUCCESS ---") # Debug
                return redirect(url_for('projects.project_detail', project_id=project_id))
            else:
                flash('Error adding task. Please check logs.', 'danger'); # print("--- projects.new_task: ERROR - add_task_to_project failed ---") # Debug
                return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None, **form_data)

    # print("--- projects.new_task: Processing GET request ---") # Debug
    return render_template('tasks/task_form.html', title='New Task', project=project, users=users_list, task=None)


@bp.route('/<project_id>/tasks/<task_id>/edit', methods=['GET', 'POST'])
@login_required
@project_owner_required # Only owner/admin edits tasks
def edit_task(project_id, task_id):
    project = get_project_by_id(project_id);
    if not project: abort(404)
    task = get_task_from_project(project_id, task_id)
    if not task: abort(404)
    users_list = User.get_all_users()
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        status = request.form.get('status')
        due_date_str = request.form.get('due_date')
        assigned_to_user_id = request.form.get('assigned_to')
        form_data = {'name': name,'description': description,'status': status,'due_date': due_date_str,'assigned_to_id': assigned_to_user_id}
        if not name:
            flash('Task name is required.', 'danger'); return render_template('tasks/task_form.html', title='Edit Task', project=project, task=task, users=users_list, **form_data)
        due_date = None
        if due_date_str:
            try: due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError: flash('Invalid date format. Use YYYY-MM-DD.', 'danger'); return render_template('tasks/task_form.html', title='Edit Task', project=project, task=task, users=users_list, **form_data)
        update_payload = {'name': name,'description': description,'status': status,'due_date': due_date,'assigned_to': assigned_to_user_id if assigned_to_user_id else None}
        if update_task_in_project(project_id, task_id, update_payload):
            flash('Task updated successfully!', 'success'); return redirect(url_for('projects.project_detail', project_id=project_id, _anchor=f'task-{task_id}'))
        else:
            flash('Error updating task, or no changes detected.', 'danger'); return render_template('tasks/task_form.html', title='Edit Task', project=project, task=task, users=users_list, **form_data)
    due_date_val = task.get('due_date').strftime('%Y-%m-%d') if task.get('due_date') else ''
    assigned_id_val = str(task.get('assigned_to')) if task.get('assigned_to') else ''
    return render_template('tasks/task_form.html', title='Edit Task', project=project, task=task, users=users_list, name=task.get('name'), description=task.get('description'), status=task.get('status'), due_date=due_date_val, assigned_to_id=assigned_id_val)


@bp.route('/<project_id>/tasks/<task_id>/update_status', methods=['POST'])
@login_required
@project_access_required # Allow view access users to update status
def update_task_status_route(project_id, task_id):
    # Add more specific permission check here if needed (e.g., only task assignee)
    new_status = request.form.get('status')
    allowed_statuses = ['To Do', 'In Progress', 'Done']
    if not new_status or new_status not in allowed_statuses: flash(f'Invalid status: {new_status}', 'warning')
    elif update_task_status_in_project(project_id, task_id, new_status): flash('Task status updated.', 'success')
    else: flash('Error updating task status.', 'danger')
    return redirect(url_for('projects.project_detail', project_id=project_id, _anchor=f'task-{task_id}'))


@bp.route('/<project_id>/tasks/<task_id>/delete', methods=['POST'])
@login_required
@project_owner_required # Only owner/admin deletes tasks
def delete_task_route(project_id, task_id):
     if delete_task_from_project(project_id, task_id): flash('Task deleted successfully.', 'success')
     else: flash('Error deleting task.', 'danger')
     return redirect(url_for('projects.project_detail', project_id=project_id))