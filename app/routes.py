# app/routes.py
from flask import (
    render_template, url_for, flash, redirect, request, abort, Blueprint, current_app, jsonify
)
from .extensions import db, bcrypt, login_manager
from .forms import (
    RegistrationForm, LoginForm, ProjectForm, TaskForm, UpdateTaskStatusForm,
    UpdateProfileForm, WorkPackageForm, MilestoneForm # Add new forms
)
from .models import User, Project, Task, WorkPackage, Milestone # Add new models
from .decorators import admin_required
from flask_login import login_user, current_user, logout_user, login_required
from mongoengine.errors import NotUniqueError, ValidationError as MongoValidationError
import logging
from datetime import datetime # Import datetime for calendar

log = logging.getLogger(__name__)

main_routes = Blueprint('main', __name__)

# --- Core Routes ---

@main_routes.route('/')
@main_routes.route('/index')
def index():
    """Landing page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard')) # Use blueprint name
    return render_template('index.html', title='Welcome')

@main_routes.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard')) # Use blueprint name
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            is_first_user = User.objects.count() == 0
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.username.data,
                        email=form.email.data,
                        password_hash=hashed_password,
                        is_admin=is_first_user)
            user.save()
            flash(f'Account created for {form.username.data}! You can now log in.', 'success')
            if is_first_user:
                flash('As the first user, you have been granted Admin privileges.', 'info')
            return redirect(url_for('main.login')) # Use blueprint name
        except NotUniqueError:
             flash('Username or Email already exists. Please choose different ones.', 'danger')
        except Exception as e:
             log.error(f"Error during registration for {form.username.data}: {e}", exc_info=True)
             flash(f'An error occurred during registration. Please try again.', 'danger')
    return render_template('register.html', title='Register', form=form)

@main_routes.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard')) # Use blueprint name
    form = LoginForm()
    if form.validate_on_submit():
        user = User.objects(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data) # Uses login_manager implicitly
            next_page = request.args.get('next')
            flash('Login Successful!', 'success')
            if next_page and next_page.startswith('/') and not next_page.startswith('//'):
                 return redirect(next_page)
            else:
                 return redirect(url_for('main.dashboard')) # Default redirect
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@main_routes.route('/logout')
@login_required
def logout():
    """Handles user logout."""
    logout_user() # Uses login_manager implicitly
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index')) # Use blueprint name

@main_routes.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    if current_user.is_admin:
        projects = Project.objects.order_by('-created_at')
        tasks = Task.objects.order_by('-created_at')
        users = User.objects.order_by('username')
        return render_template('dashboard.html', title='Admin Dashboard',
                               projects=projects, tasks=tasks, users=users)
    else:
        assigned_tasks = Task.objects(assigned_to=current_user).order_by('due_date', 'status')
        return render_template('dashboard.html', title='My Dashboard', assigned_tasks=assigned_tasks)


# --- Profile Routes ---

@main_routes.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Displays and handles updates for the user's profile."""
    form = UpdateProfileForm(
        original_username=current_user.username,
        original_email=current_user.email
    )
    if form.validate_on_submit():
        try:
            needs_save = False
            if current_user.username != form.username.data:
                 # username is readonly in example template, so skip update check
                 pass
            if current_user.email != form.email.data:
                current_user.email = form.email.data
                needs_save = True
            if current_user.theme != form.theme.data:
                current_user.theme = form.theme.data
                needs_save = True

            if needs_save:
                current_user.save()
                flash('Your profile has been updated successfully!', 'success')
                log.info(f"User '{current_user.username}' updated profile. Theme set to '{current_user.theme}'.")
            else:
                flash('No changes detected in profile.', 'info')
            return redirect(url_for('main.profile'))

        except NotUniqueError:
             flash('Update failed. The chosen email is already in use by another account.', 'danger')
        except MongoValidationError as e:
            log.error(f"Validation error updating profile for user {current_user.username}: {e}", exc_info=True)
            flash(f'Update failed due to a validation error: {e}', 'danger')
        except Exception as e:
            log.error(f"Unexpected error updating profile for user {current_user.username}: {e}", exc_info=True)
            flash('An unexpected error occurred while updating your profile.', 'danger')

    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.theme.data = getattr(current_user, 'theme', None) or form.theme.default
    elif request.method == 'POST' and not form.validate_on_submit():
         log.warning(f"Profile update form validation failed for user {current_user.username}: {form.errors}")

    return render_template('profile.html', title='My Profile', form=form)


# --- Project Routes ---

@main_routes.route('/projects')
@login_required
def list_projects():
    """Lists all projects."""
    projects = Project.objects.order_by('-created_at')
    return render_template('projects.html', title='Projects', projects=projects)

@main_routes.route('/project/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_project():
    """Handles creation of a new project (Admin only)."""
    form = ProjectForm()
    if form.validate_on_submit():
        try:
            project = Project(name=form.name.data,
                              description=form.description.data,
                              created_by=current_user)
            project.save()
            flash('Project created successfully!', 'success')
            return redirect(url_for('main.list_projects'))
        except NotUniqueError:
             flash('A project with this name already exists.', 'danger')
        except MongoValidationError as e:
             log.error(f"Validation error creating project '{form.name.data}': {e}", exc_info=True)
             flash(f'Error creating project: {e}', 'danger')
        except Exception as e:
             log.error(f"Unexpected error creating project '{form.name.data}': {e}", exc_info=True)
             flash(f'An unexpected error occurred while creating the project.', 'danger')
    return render_template('create_project.html', title='New Project', form=form)

# --- UPDATED: Project Detail Route ---
@main_routes.route('/project/<project_id>')
@login_required
def project_detail(project_id):
    """Shows details, WPs, Milestones, and Tasks."""
    project = Project.objects(pk=project_id).first_or_404()
    work_packages = WorkPackage.objects(project=project).order_by('start_date', 'name')
    milestones = Milestone.objects(project=project).order_by('target_date')
    tasks = Task.objects(project=project).order_by('work_package', 'status', 'due_date')

    return render_template(
        'project_detail.html',
        title=project.name,
        project=project,
        work_packages=work_packages,
        milestones=milestones,
        tasks=tasks
    )

# --- NEW: Create Work Package Route ---
@main_routes.route('/project/<project_id>/work_package/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_work_package(project_id):
    project = Project.objects(pk=project_id).first_or_404()
    form = WorkPackageForm()
    if form.validate_on_submit():
        try:
            wp = WorkPackage(
                name=form.name.data,
                description=form.description.data,
                project=project,
                created_by=current_user,
                start_date=form.start_date.data,
                end_date=form.end_date.data
            )
            wp.save()
            flash('Work Package created successfully!', 'success')
            return redirect(url_for('main.project_detail', project_id=project.id))
        except MongoValidationError as e:
            log.error(f"Validation error creating WP for project {project_id}: {e}", exc_info=True)
            flash(f'Error creating Work Package: {e}', 'danger')
        except Exception as e:
            log.error(f"Unexpected error creating WP for project {project_id}: {e}", exc_info=True)
            flash('An unexpected error occurred.', 'danger')
    return render_template('create_work_package.html', title='New Work Package', form=form, project=project)

# --- NEW: Create Milestone Route ---
@main_routes.route('/project/<project_id>/milestone/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_milestone(project_id):
    project = Project.objects(pk=project_id).first_or_404()
    form = MilestoneForm()
    if form.validate_on_submit():
        try:
            milestone = Milestone(
                name=form.name.data,
                description=form.description.data,
                project=project,
                target_date=form.target_date.data,
                created_by=current_user
            )
            milestone.save()
            flash('Milestone created successfully!', 'success')
            return redirect(url_for('main.project_roadmap', project_id=project.id))
        except MongoValidationError as e:
            log.error(f"Validation error creating Milestone for project {project_id}: {e}", exc_info=True)
            flash(f'Error creating Milestone: {e}', 'danger')
        except Exception as e:
            log.error(f"Unexpected error creating Milestone for project {project_id}: {e}", exc_info=True)
            flash('An unexpected error occurred.', 'danger')
    return render_template('create_milestone.html', title='New Milestone', form=form, project=project)

# --- NEW: Project Roadmap Route ---
@main_routes.route('/project/<project_id>/roadmap')
@login_required
def project_roadmap(project_id):
    project = Project.objects(pk=project_id).first_or_404()
    milestones = Milestone.objects(project=project).order_by('target_date')
    return render_template('roadmap.html', title=f"{project.name} - Roadmap", project=project, milestones=milestones)

# --- UPDATED: Create Task Route ---
@main_routes.route('/project/<project_id>/task/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_task(project_id):
    project = Project.objects(pk=project_id).first_or_404()
    form = TaskForm(project_id=project_id) # Pass project_id to populate WPs

    if form.validate_on_submit():
        try:
            assigned_user = User.objects(pk=form.assigned_to.data).first()
            if not assigned_user:
                flash('Selected user for assignment not found.', 'danger')
                return render_template('create_task.html', title='New Task', form=form, project=project)

            selected_wp = None
            if form.work_package.data:
                selected_wp = WorkPackage.objects(pk=form.work_package.data, project=project).first()
                if not selected_wp:
                    flash('Selected Work Package not found for this project.', 'warning')
                    selected_wp = None

            task = Task(
                title=form.title.data, description=form.description.data, project=project,
                work_package=selected_wp, assigned_to=assigned_user, created_by=current_user,
                status=form.status.data, due_date=form.due_date.data
            )
            task.save()
            flash('Task created and assigned successfully!', 'success')
            return redirect(url_for('main.project_detail', project_id=project.id))
        except MongoValidationError as e:
             log.error(f"Validation error creating task '{form.title.data}' for project {project_id}: {e}", exc_info=True)
             flash(f'Error creating task: {e}', 'danger')
        except Exception as e:
             log.error(f"Unexpected error creating task '{form.title.data}' for project {project_id}: {e}", exc_info=True)
             flash(f'An unexpected error occurred while creating the task.', 'danger')
    elif request.method == 'POST':
         log.warning(f"Task creation form validation failed for project {project_id}: {form.errors}")

    return render_template('create_task.html', title='New Task', form=form, project=project)

# --- UPDATED: Task Detail Route ---
@main_routes.route('/task/<task_id>', methods=['GET', 'POST'])
@login_required
def task_detail(task_id):
    task = Task.objects(pk=task_id).first_or_404()
    can_update = (current_user == task.assigned_to or current_user.is_admin)
    form = UpdateTaskStatusForm(obj=task)
    if can_update and form.validate_on_submit():
        try:
            original_status = task.status
            task.status = form.status.data
            task.save()
            log.info(f"User '{current_user.username}' updated task '{task_id}' status from '{original_status}' to '{task.status}'.")
            flash('Task status updated successfully!', 'success')
            return redirect(url_for('main.task_detail', task_id=task.id))
        except MongoValidationError as e:
             log.error(f"Validation error updating task {task_id} status: {e}", exc_info=True)
             flash(f'Error updating task status: {e}', 'danger')
        except Exception as e:
             log.error(f"Unexpected error updating task {task_id} status: {e}", exc_info=True)
             flash(f'An unexpected error occurred while updating status.', 'danger')

    return render_template('task_detail.html', title=task.title, task=task, form=form, can_update=can_update)


# --- NEW: Calendar Routes ---

@main_routes.route('/calendar')
@main_routes.route('/project/<project_id>/calendar') # Allow project-specific calendar
@login_required
def project_calendar(project_id=None):
    """Displays the calendar view."""
    project = None
    if project_id:
        project = Project.objects(pk=project_id).first_or_404()
        title = f"{project.name} - Calendar"
    else:
        title = "My Calendar" # Or "All Projects Calendar"
    return render_template('calendar.html', title=title, project=project)

@main_routes.route('/calendar/events')
@main_routes.route('/project/<project_id>/calendar/events') # API endpoint for events
@login_required
def calendar_events(project_id=None):
    """Provides event data as JSON for FullCalendar."""
    events = []
    now = datetime.utcnow()
    task_query_args = {}
    milestone_query_args = {}

    if project_id:
        project = Project.objects(pk=project_id).first_or_404()
        task_query_args['project'] = project
        milestone_query_args['project'] = project
    else:
         # General calendar shows tasks assigned to user across all projects
         task_query_args['assigned_to'] = current_user
         # General calendar shows all milestones (adjust scope if needed)
         pass

    # --- Fetch Tasks with due dates ---
    tasks = Task.objects(**task_query_args).exclude('description')
    for task in tasks:
        if task.due_date:
            event_class = 'event-task'
            if task.status == 'Done': event_class += ' event-done'
            elif task.due_date < now: event_class += ' event-overdue'
            events.append({
                'title': f"Task: {task.title}", 'start': task.due_date.isoformat(),
                'end': task.due_date.isoformat(), 'url': url_for('main.task_detail', task_id=task.id),
                'className': event_class,
                'extendedProps': {'type': 'task', 'status': task.status, 'project': task.project.name}
            })

    # --- Fetch Milestones ---
    milestones = Milestone.objects(**milestone_query_args)
    for milestone in milestones:
         events.append({
            'title': f"Milestone: {milestone.name}", 'start': milestone.target_date.isoformat(),
            'end': milestone.target_date.isoformat(), 'url': url_for('main.project_roadmap', project_id=milestone.project.id),
             'className': 'event-milestone',
             'extendedProps': {'type': 'milestone', 'project': milestone.project.name}
         })

    return jsonify(events)

# --- Admin Routes ---

@main_routes.route('/admin')
@login_required
@admin_required
def admin_console():
    user_count = User.objects.count()
    project_count = Project.objects.count()
    task_count = Task.objects.count()
    return render_template('admin/console.html', title='Admin Console',
                           user_count=user_count, project_count=project_count, task_count=task_count)

@main_routes.route('/admin/users')
@login_required
@admin_required
def admin_list_users():
    users = User.objects.order_by('username')
    return render_template('admin/users.html', title='Manage Users', users=users)

@main_routes.route('/admin/user/<user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def admin_toggle_admin(user_id):
    user_to_modify = User.objects(pk=user_id).first_or_404()
    if user_to_modify == current_user and User.objects(is_admin=True).count() <= 1:
         flash('Cannot remove admin status from the only remaining admin.', 'danger')
         return redirect(url_for('main.admin_list_users'))
    try:
        original_admin_status = user_to_modify.is_admin
        user_to_modify.is_admin = not user_to_modify.is_admin
        user_to_modify.save()
        status = "granted" if user_to_modify.is_admin else "revoked"
        log.info(f"Admin '{current_user.username}' {status} admin status for user '{user_to_modify.username}'.")
        flash(f'Admin status {status} for user {user_to_modify.username}.', 'success')
    except Exception as e:
        log.error(f"Error toggling admin status for user {user_id} by admin {current_user.username}: {e}", exc_info=True)
        flash(f'Error updating user status: {e}', 'danger')
    return redirect(url_for('main.admin_list_users'))


# --- Error Handlers (Registered on Blueprint) ---

@main_routes.app_errorhandler(404)
def not_found_error(error):
    log.warning(f"404 Not Found error for URL: {request.url} - {error}")
    return render_template('errors/404.html'), 404

@main_routes.app_errorhandler(500)
def internal_error(error):
    log.error(f"500 Internal Server Error for URL: {request.url}", exc_info=error)
    return render_template('errors/500.html'), 500