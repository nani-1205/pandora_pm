# app/routes.py
from flask import (
    render_template, url_for, flash, redirect, request, abort, Blueprint, current_app
)
# Import extensions initialized in __init__
from . import db, bcrypt, login_manager # Import login_manager if needed for decorators directly

# Import Forms, Models, Decorators
from .forms import (
    RegistrationForm, LoginForm, ProjectForm, TaskForm, UpdateTaskStatusForm
)
from .models import User, Project, Task
from .decorators import admin_required

# Import Flask-Login utilities
from flask_login import login_user, current_user, logout_user, login_required

# Import MongoEngine Errors
from mongoengine.errors import NotUniqueError, ValidationError as MongoValidationError

# Logging
import logging
log = logging.getLogger(__name__)


# Create a Blueprint instance
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
            # Check if this is the first user
            is_first_user = User.objects.count() == 0

            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.username.data,
                        email=form.email.data,
                        password_hash=hashed_password,
                        is_admin=is_first_user) # Make first user admin
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
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login Successful!', 'success')
            # Basic security check for next_page to prevent open redirect
            if next_page and next_page.startswith('/') and not next_page.startswith('//'):
                 # Consider using url_has_allowed_host_and_scheme from werkzeug.utils for better security
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
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index')) # Use blueprint name

@main_routes.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    if current_user.is_admin:
        # Admin Dashboard: Show project overview, user stats, etc.
        # Ensure templates use url_for('main.project_detail') etc.
        projects = Project.objects.order_by('-created_at')
        tasks = Task.objects.order_by('-created_at') # Or filter by status
        users = User.objects.order_by('username')
        return render_template('dashboard.html', title='Admin Dashboard',
                               projects=projects, tasks=tasks, users=users)
    else:
        # Regular User Dashboard: Show assigned tasks
        # Ensure templates use url_for('main.task_detail') etc.
        assigned_tasks = Task.objects(assigned_to=current_user).order_by('due_date', 'status')
        return render_template('dashboard.html', title='My Dashboard', assigned_tasks=assigned_tasks)

# --- Project Routes ---

@main_routes.route('/projects')
@login_required
def list_projects():
    """Lists all projects."""
    # Ensure template uses url_for('main.project_detail')
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
            return redirect(url_for('main.list_projects')) # Use blueprint name
        except NotUniqueError:
             flash('A project with this name already exists.', 'danger')
        except MongoValidationError as e:
             log.error(f"Validation error creating project '{form.name.data}': {e}", exc_info=True)
             flash(f'Error creating project: {e}', 'danger')
        except Exception as e:
             log.error(f"Unexpected error creating project '{form.name.data}': {e}", exc_info=True)
             flash(f'An unexpected error occurred while creating the project.', 'danger')
    return render_template('create_project.html', title='New Project', form=form)

@main_routes.route('/project/<project_id>')
@login_required
def project_detail(project_id):
    """Shows details of a specific project and its tasks."""
    # Ensure template uses url_for('main.create_task'), url_for('main.task_detail')
    project = Project.objects(pk=project_id).first_or_404()
    tasks = Task.objects(project=project).order_by('status', 'due_date')
    return render_template('project_detail.html', title=project.name, project=project, tasks=tasks)

# --- Task Routes ---

@main_routes.route('/project/<project_id>/task/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_task(project_id):
    """Handles creation of a new task within a project (Admin only)."""
    project = Project.objects(pk=project_id).first_or_404()
    form = TaskForm() # Populates users dynamically via __init__ in the form

    if form.validate_on_submit():
        try:
            assigned_user = User.objects(pk=form.assigned_to.data).first()
            if not assigned_user:
                flash('Selected user for assignment not found.', 'danger')
                # Re-render form with validation error implicitly handled by WTForms
                return render_template('create_task.html', title='New Task', form=form, project=project)

            task = Task(title=form.title.data,
                        description=form.description.data,
                        project=project,
                        assigned_to=assigned_user,
                        created_by=current_user,
                        status=form.status.data,
                        due_date=form.due_date.data)
            task.save()
            flash('Task created and assigned successfully!', 'success')
            return redirect(url_for('main.project_detail', project_id=project.id)) # Use blueprint name
        except MongoValidationError as e:
             log.error(f"Validation error creating task '{form.title.data}' for project {project_id}: {e}", exc_info=True)
             flash(f'Error creating task: {e}', 'danger')
        except Exception as e:
             log.error(f"Unexpected error creating task '{form.title.data}' for project {project_id}: {e}", exc_info=True)
             flash(f'An unexpected error occurred while creating the task.', 'danger')
    elif request.method == 'POST':
         # Log form errors if validation fails on POST
         log.warning(f"Task creation form validation failed for project {project_id}: {form.errors}")

    return render_template('create_task.html', title='New Task', form=form, project=project)

@main_routes.route('/task/<task_id>', methods=['GET', 'POST'])
@login_required
def task_detail(task_id):
    """Shows task details and allows status updates by assigned user or admin."""
    task = Task.objects(pk=task_id).first_or_404()

    # Authorization: Only assigned user or admin can update status
    can_update = (current_user == task.assigned_to or current_user.is_admin)

    form = UpdateTaskStatusForm(obj=task) # Pre-populate form with current status

    if can_update and form.validate_on_submit():
        try:
            original_status = task.status # Optional: Store original status for logging
            task.status = form.status.data
            task.save()
            log.info(f"User '{current_user.username}' updated task '{task_id}' status from '{original_status}' to '{task.status}'.")
            flash('Task status updated successfully!', 'success')
            # Redirect back to the task detail page
            return redirect(url_for('main.task_detail', task_id=task.id)) # Use blueprint name
        except MongoValidationError as e:
             log.error(f"Validation error updating task {task_id} status: {e}", exc_info=True)
             flash(f'Error updating task status: {e}', 'danger')
        except Exception as e:
             log.error(f"Unexpected error updating task {task_id} status: {e}", exc_info=True)
             flash(f'An unexpected error occurred while updating status.', 'danger')

    # Ensure template uses url_for('main.project_detail')
    return render_template('task_detail.html', title=task.title, task=task, form=form, can_update=can_update)


# --- Admin Routes ---

@main_routes.route('/admin')
@login_required
@admin_required
def admin_console():
    """Admin console main page."""
    # Ensure template uses url_for('main.admin_list_users') etc.
    user_count = User.objects.count()
    project_count = Project.objects.count()
    task_count = Task.objects.count()
    return render_template('admin/console.html', title='Admin Console',
                           user_count=user_count, project_count=project_count, task_count=task_count)

@main_routes.route('/admin/users')
@login_required
@admin_required
def admin_list_users():
    """Lists all users for the admin."""
    # Ensure template uses url_for('main.admin_toggle_admin')
    users = User.objects.order_by('username')
    return render_template('admin/users.html', title='Manage Users', users=users)

@main_routes.route('/admin/user/<user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def admin_toggle_admin(user_id):
    """Toggles the admin status of a user."""
    user_to_modify = User.objects(pk=user_id).first_or_404()

    # Basic safety: Prevent the only admin from removing their own admin status
    if user_to_modify == current_user and User.objects(is_admin=True).count() <= 1:
         flash('Cannot remove admin status from the only remaining admin.', 'danger')
         return redirect(url_for('main.admin_list_users')) # Use blueprint name

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

    return redirect(url_for('main.admin_list_users')) # Use blueprint name


# --- Error Handlers (Registered on Blueprint) ---

@main_routes.app_errorhandler(404)
def not_found_error(error):
    """Handles 404 errors."""
    log.warning(f"404 Not Found error for URL: {request.url} - {error}")
    return render_template('errors/404.html'), 404

@main_routes.app_errorhandler(500)
def internal_error(error):
    """Handles 500 internal server errors."""
    # Log the actual exception
    log.error(f"500 Internal Server Error for URL: {request.url}", exc_info=error)
    # db.session.rollback() # Not needed for MongoEngine usually
    return render_template('errors/500.html'), 500

# You can add more specific error handlers if needed (e.g., 403 Forbidden)
# @main_routes.app_errorhandler(403)
# def forbidden_error(error):
#     log.warning(f"403 Forbidden error for URL: {request.url} by user '{current_user.username if current_user.is_authenticated else 'anonymous'}' - {error}")
#     return render_template('errors/403.html'), 403