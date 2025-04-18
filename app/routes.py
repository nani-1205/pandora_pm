# app/routes.py
from flask import render_template, url_for, flash, redirect, request, abort
from . import app, db, bcrypt # Import from __init__
from .forms import RegistrationForm, LoginForm, ProjectForm, TaskForm, UpdateTaskStatusForm
from .models import User, Project, Task
from .decorators import admin_required
from flask_login import login_user, current_user, logout_user, login_required
from mongoengine.errors import NotUniqueError, ValidationError as MongoValidationError

@app.route('/')
@app.route('/index')
def index():
    """Landing page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html', title='Welcome') # Simple landing or redirect

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
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
            return redirect(url_for('login'))
        except NotUniqueError:
             flash('Username or Email already exists. Please choose different ones.', 'danger')
        except Exception as e:
             flash(f'An error occurred during registration: {e}', 'danger')
             # Log the error e for debugging
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.objects(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login Successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
@login_required
def logout():
    """Handles user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    if current_user.is_admin:
        # Admin Dashboard: Show project overview, user stats, etc.
        projects = Project.objects.order_by('-created_at')
        tasks = Task.objects.order_by('-created_at') # Or filter by status
        users = User.objects.order_by('username')
        return render_template('dashboard.html', title='Admin Dashboard',
                               projects=projects, tasks=tasks, users=users)
    else:
        # Regular User Dashboard: Show assigned tasks
        assigned_tasks = Task.objects(assigned_to=current_user).order_by('due_date', 'status')
        return render_template('dashboard.html', title='My Dashboard', assigned_tasks=assigned_tasks)

# --- Project Routes ---
@app.route('/projects')
@login_required
def list_projects():
    """Lists all projects (visible to all logged-in users for now)."""
    projects = Project.objects.order_by('-created_at')
    return render_template('projects.html', title='Projects', projects=projects)

@app.route('/project/new', methods=['GET', 'POST'])
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
            return redirect(url_for('list_projects'))
        except NotUniqueError:
             flash('A project with this name already exists.', 'danger')
        except MongoValidationError as e:
             flash(f'Error creating project: {e}', 'danger')
    return render_template('create_project.html', title='New Project', form=form)

@app.route('/project/<project_id>')
@login_required
def project_detail(project_id):
    """Shows details of a specific project and its tasks."""
    project = Project.objects(pk=project_id).first_or_404()
    tasks = Task.objects(project=project).order_by('status', 'due_date')
    # Check if user should see this (e.g., admin or assigned to a task in project)
    # Simple check for now: all logged-in users can see details
    return render_template('project_detail.html', title=project.name, project=project, tasks=tasks)

# --- Task Routes ---
@app.route('/project/<project_id>/task/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_task(project_id):
    """Handles creation of a new task within a project (Admin only)."""
    project = Project.objects(pk=project_id).first_or_404()
    form = TaskForm() # Populates users dynamically

    if form.validate_on_submit():
        try:
            assigned_user = User.objects(pk=form.assigned_to.data).first()
            if not assigned_user:
                flash('Selected user not found.', 'danger')
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
            return redirect(url_for('project_detail', project_id=project.id))
        except MongoValidationError as e:
             flash(f'Error creating task: {e}', 'danger')
        except Exception as e:
             flash(f'An unexpected error occurred: {e}', 'danger')
             # Log the error e

    return render_template('create_task.html', title='New Task', form=form, project=project)

@app.route('/task/<task_id>', methods=['GET', 'POST'])
@login_required
def task_detail(task_id):
    """Shows task details and allows status updates by assigned user."""
    task = Task.objects(pk=task_id).first_or_404()

    # Authorization: Only assigned user or admin can update status
    can_update = (current_user == task.assigned_to or current_user.is_admin)

    form = UpdateTaskStatusForm(obj=task) # Pre-populate form with current status

    if can_update and form.validate_on_submit():
        try:
            task.status = form.status.data
            task.save()
            flash('Task status updated successfully!', 'success')
            # Redirect back to the task detail or the project detail page
            return redirect(url_for('task_detail', task_id=task.id))
        except MongoValidationError as e:
             flash(f'Error updating task status: {e}', 'danger')

    return render_template('task_detail.html', title=task.title, task=task, form=form, can_update=can_update)


# --- Admin Routes ---
@app.route('/admin')
@login_required
@admin_required
def admin_console():
    """Admin console main page."""
    user_count = User.objects.count()
    project_count = Project.objects.count()
    task_count = Task.objects.count()
    return render_template('admin/console.html', title='Admin Console',
                           user_count=user_count, project_count=project_count, task_count=task_count)

@app.route('/admin/users')
@login_required
@admin_required
def admin_list_users():
    """Lists all users for the admin."""
    users = User.objects.order_by('username')
    return render_template('admin/users.html', title='Manage Users', users=users)

@app.route('/admin/user/<user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def admin_toggle_admin(user_id):
    """Toggles the admin status of a user."""
    user_to_modify = User.objects(pk=user_id).first_or_404()

    # Basic safety: Prevent the only admin from removing their own admin status
    # A more robust check might be needed in complex scenarios
    if user_to_modify == current_user and User.objects(is_admin=True).count() <= 1:
         flash('Cannot remove admin status from the only remaining admin.', 'danger')
         return redirect(url_for('admin_list_users'))

    try:
        user_to_modify.is_admin = not user_to_modify.is_admin
        user_to_modify.save()
        status = "granted" if user_to_modify.is_admin else "revoked"
        flash(f'Admin status {status} for user {user_to_modify.username}.', 'success')
    except Exception as e:
        flash(f'Error updating user status: {e}', 'danger')

    return redirect(url_for('admin_list_users'))

# Add error handlers (404, 500) if desired
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    # db.session.rollback() # If using SQLalchemy, rollback session
    return render_template('errors/500.html'), 500