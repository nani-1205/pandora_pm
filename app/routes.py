# app/routes.py
from flask import (
    render_template, url_for, flash, redirect, request, abort, Blueprint, current_app, jsonify
)
from .extensions import db, bcrypt, login_manager
from .forms import ( # Import ALL forms used
    RegistrationForm, LoginForm, ProjectForm, TaskForm, UpdateTaskStatusForm,
    UpdateProfileForm, WorkPackageForm, MilestoneForm, CalendarEventForm,
    ChatGroupForm, ChatMessageForm # Add chat forms
)
from .models import ( # Import ALL models used
    User, Project, Task, WorkPackage, Milestone, CalendarEvent,
    ChatGroup, ChatMessage # Add chat models
)
from .decorators import admin_required
from flask_login import login_user, current_user, logout_user, login_required
from mongoengine.errors import NotUniqueError, ValidationError as MongoValidationError
import logging
from datetime import datetime, time, timedelta # Import datetime, time, timedelta

log = logging.getLogger(__name__)
main_routes = Blueprint('main', __name__)

# --- Core Routes ---
@main_routes.route('/')
@main_routes.route('/index')
def index():
    if current_user.is_authenticated: return redirect(url_for('main.dashboard'))
    return render_template('index.html', title='Welcome')

@main_routes.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            is_first_user = User.objects.count() == 0
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.username.data, email=form.email.data,
                        password_hash=hashed_password, is_admin=is_first_user)
            user.save()
            flash(f'Account created for {form.username.data}! You can now log in.', 'success')
            if is_first_user: flash('As the first user, you have been granted Admin privileges.', 'info')
            return redirect(url_for('main.login'))
        except NotUniqueError: flash('Username or Email already exists.', 'danger')
        except Exception as e: log.error(f"Reg Error: {e}", exc_info=True); flash('Error during registration.', 'danger')
    return render_template('register.html', title='Register', form=form)

@main_routes.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.objects(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login Successful!', 'success')
            if next_page and next_page.startswith('/') and not next_page.startswith('//'): return redirect(next_page)
            else: return redirect(url_for('main.dashboard'))
        else: flash('Login Unsuccessful. Check email/password', 'danger')
    return render_template('login.html', title='Login', form=form)

@main_routes.route('/logout')
@login_required
def logout():
    logout_user(); flash('Logged out.', 'info'); return redirect(url_for('main.index'))

@main_routes.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        projects = Project.objects.order_by('-created_at'); tasks = Task.objects.order_by('-created_at'); users = User.objects.order_by('username')
        return render_template('dashboard.html', title='Admin Dashboard', projects=projects, tasks=tasks, users=users)
    else:
        assigned_tasks = Task.objects(assigned_to=current_user).order_by('due_date', 'status')
        return render_template('dashboard.html', title='My Dashboard', assigned_tasks=assigned_tasks)

# --- Profile Routes ---
@main_routes.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateProfileForm(original_username=current_user.username, original_email=current_user.email)
    if form.validate_on_submit():
        try:
            needs_save = False
            if current_user.email != form.email.data: current_user.email = form.email.data; needs_save = True
            if current_user.theme != form.theme.data: current_user.theme = form.theme.data; needs_save = True
            if needs_save: current_user.save(); flash('Profile updated!', 'success'); log.info(f"User '{current_user.username}' updated profile.")
            else: flash('No changes detected.', 'info')
            return redirect(url_for('main.profile'))
        except NotUniqueError: flash('Update failed. Email already in use.', 'danger')
        except Exception as e: log.error(f"Profile update error: {e}", exc_info=True); flash('Error updating profile.', 'danger')
    elif request.method == 'GET':
        form.username.data = current_user.username; form.email.data = current_user.email
        form.theme.data = getattr(current_user, 'theme', None) or form.theme.default
    elif not form.validate_on_submit(): log.warning(f"Profile validation failed: {form.errors}")
    return render_template('profile.html', title='My Profile', form=form)

# --- Project Routes ---
@main_routes.route('/projects')
@login_required
def list_projects():
    projects = Project.objects.order_by('-created_at'); return render_template('projects.html', title='Projects', projects=projects)

@main_routes.route('/project/new', methods=['GET', 'POST'])
@login_required @admin_required
def create_project():
    form = ProjectForm()
    if form.validate_on_submit():
        try:
            project = Project(name=form.name.data, description=form.description.data, created_by=current_user); project.save()
            flash('Project created!', 'success'); return redirect(url_for('main.list_projects'))
        except NotUniqueError: flash('Project name exists.', 'danger')
        except Exception as e: log.error(f"Project creation error: {e}", exc_info=True); flash('Error creating project.', 'danger')
    return render_template('create_project.html', title='New Project', form=form)

@main_routes.route('/project/<project_id>')
@login_required
def project_detail(project_id):
    project = Project.objects(pk=project_id).first_or_404()
    work_packages = WorkPackage.objects(project=project).order_by('start_date', 'name')
    milestones = Milestone.objects(project=project).order_by('target_date')
    tasks = Task.objects(project=project).order_by('work_package', 'status', 'due_date')
    return render_template('project_detail.html', title=project.name, project=project,
                           work_packages=work_packages, milestones=milestones, tasks=tasks)

# --- Work Package Routes ---
@main_routes.route('/project/<project_id>/work_package/new', methods=['GET', 'POST'])
@login_required @admin_required
def create_work_package(project_id):
    project = Project.objects(pk=project_id).first_or_404()
    form = WorkPackageForm()
    if form.validate_on_submit():
        try:
            wp = WorkPackage(name=form.name.data, description=form.description.data, project=project, created_by=current_user, start_date=form.start_date.data, end_date=form.end_date.data)
            wp.save(); flash('Work Package created!', 'success'); return redirect(url_for('main.project_detail', project_id=project.id))
        except Exception as e: log.error(f"WP creation error: {e}", exc_info=True); flash('Error creating WP.', 'danger')
    return render_template('create_work_package.html', title='New Work Package', form=form, project=project)

# --- Milestone Routes ---
@main_routes.route('/project/<project_id>/milestone/new', methods=['GET', 'POST'])
@login_required @admin_required
def create_milestone(project_id):
    project = Project.objects(pk=project_id).first_or_404()
    form = MilestoneForm()
    if form.validate_on_submit():
        try:
            milestone = Milestone(name=form.name.data, description=form.description.data, project=project, target_date=form.target_date.data, created_by=current_user)
            milestone.save(); flash('Milestone created!', 'success'); return redirect(url_for('main.project_roadmap', project_id=project.id))
        except Exception as e: log.error(f"Milestone creation error: {e}", exc_info=True); flash('Error creating milestone.', 'danger')
    return render_template('create_milestone.html', title='New Milestone', form=form, project=project)

@main_routes.route('/project/<project_id>/roadmap')
@login_required
def project_roadmap(project_id):
    project = Project.objects(pk=project_id).first_or_404(); milestones = Milestone.objects(project=project).order_by('target_date')
    return render_template('roadmap.html', title=f"{project.name} - Roadmap", project=project, milestones=milestones)

# --- Task Routes ---
@main_routes.route('/project/<project_id>/task/new', methods=['GET', 'POST'])
@login_required @admin_required
def create_task(project_id):
    project = Project.objects(pk=project_id).first_or_404(); form = TaskForm(project_id=project_id)
    if form.validate_on_submit():
        try:
            assigned_user = User.objects(pk=form.assigned_to.data).first()
            if not assigned_user: flash('Assignee not found.', 'danger'); return render_template('create_task.html', title='New Task', form=form, project=project)
            selected_wp = WorkPackage.objects(pk=form.work_package.data, project=project).first() if form.work_package.data else None
            if form.work_package.data and not selected_wp: flash('WP invalid.', 'warning'); selected_wp = None
            task = Task(title=form.title.data, description=form.description.data, project=project, work_package=selected_wp, assigned_to=assigned_user, created_by=current_user, status=form.status.data, due_date=form.due_date.data)
            task.save(); flash('Task created!', 'success'); return redirect(url_for('main.project_detail', project_id=project.id))
        except Exception as e: log.error(f"Task creation error: {e}", exc_info=True); flash('Error creating task.', 'danger')
    elif request.method == 'POST': log.warning(f"Task validation failed: {form.errors}")
    return render_template('create_task.html', title='New Task', form=form, project=project)

@main_routes.route('/task/<task_id>', methods=['GET', 'POST'])
@login_required
def task_detail(task_id):
    task = Task.objects(pk=task_id).first_or_404(); can_update = (current_user == task.assigned_to or current_user.is_admin); form = UpdateTaskStatusForm(obj=task)
    if can_update and form.validate_on_submit():
        try: task.status = form.status.data; task.save(); flash('Task status updated!', 'success'); return redirect(url_for('main.task_detail', task_id=task.id))
        except Exception as e: log.error(f"Task status update error: {e}", exc_info=True); flash('Error updating status.', 'danger')
    return render_template('task_detail.html', title=task.title, task=task, form=form, can_update=can_update)

# --- Calendar Routes ---
@main_routes.route('/calendar')
@main_routes.route('/project/<project_id>/calendar')
@login_required
def project_calendar(project_id=None):
    project = Project.objects(pk=project_id).first_or_404() if project_id else None
    title = f"{project.name} - Calendar" if project else "My Calendar"
    return render_template('calendar.html', title=title, project=project)

@main_routes.route('/calendar/events')
@main_routes.route('/project/<project_id>/calendar/events')
@login_required
def calendar_events(project_id=None):
    events, now = [], datetime.utcnow()
    task_q, ms_q, ce_q = {}, {}, {}; project = Project.objects(pk=project_id).first_or_404() if project_id else None
    if project: task_q['project'] = ms_q['project'] = ce_q['project'] = project
    else: task_q['assigned_to'] = current_user; ce_q['created_by'] = current_user; ce_q['project'] = None
    # Tasks
    for task in Task.objects(**task_q).only('id', 'title', 'due_date', 'status', 'project'):
        if task.due_date:
            cls = 'event-task'; status = task.status; project_name = task.project.name
            if status == 'Done': cls += ' event-done'
            elif task.due_date < now: cls += ' event-overdue'
            events.append({'id': f'task_{task.id}', 'title': f"Task: {task.title}", 'start': task.due_date.isoformat(), 'allDay': True,
                           'url': url_for('main.task_detail', task_id=task.id), 'className': cls, 'extendedProps': {'type': 'task', 'status': status, 'project': project_name}})
    # Milestones
    for ms in Milestone.objects(**ms_q).only('id', 'name', 'target_date', 'project'):
        events.append({'id': f'milestone_{ms.id}', 'title': f"Milestone: {ms.name}", 'start': ms.target_date.isoformat(), 'allDay': True,
                       'url': url_for('main.project_roadmap', project_id=ms.project.id), 'className': 'event-milestone', 'extendedProps': {'type': 'milestone', 'project': ms.project.name}})
    # Custom Events
    for event in CalendarEvent.objects(**ce_q).only('id', 'title', 'start_time', 'end_time', 'all_day', 'project', 'description'): events.append(event.to_fc_event())
    return jsonify(events)

@main_routes.route('/calendar/events/new', methods=['POST'])
@login_required
def create_calendar_event_api():
    project, data = None, request.get_json()
    if not data: return jsonify({'status': 'error', 'message': 'Invalid request data.'}), 400
    project_id = data.get('project_id'); title = data.get('title')
    if project_id: project = Project.objects(pk=project_id).first()
    if not title: return jsonify({'status': 'error', 'message': 'Title required.'}), 400
    try:
        start_str, end_str, all_day = data.get('start', '').replace('Z', '+00:00'), data.get('end', '').replace('Z', '+00:00'), data.get('allDay', False)
        start_dt = datetime.fromisoformat(start_str.split('T')[0] + 'T00:00:00') if all_day else datetime.fromisoformat(start_str)
        if all_day:
            end_dt = datetime.combine(start_dt.date(), time.max)
            if end_str: end_dt_from_cal = datetime.fromisoformat(end_str.split('T')[0] + 'T00:00:00');
            if end_dt_from_cal.date() > start_dt.date(): end_dt = datetime.combine(end_dt_from_cal.date() - timedelta(days=1), time.max)
        else: end_dt = datetime.fromisoformat(end_str)
        if not all_day and end_dt <= start_dt: return jsonify({'status': 'error', 'message': 'End time must be after start.'}), 400
    except Exception as e: return jsonify({'status': 'error', 'message': f'Invalid date format: {e}'}), 400
    try:
        new_event = CalendarEvent(title=title, description=data.get('description'), start_time=start_dt, end_time=end_dt, all_day=all_day, created_by=current_user, project=project)
        new_event.save(); log.info(f"User '{current_user.username}' created event '{new_event.title}'")
        return jsonify({'status': 'success', 'message': 'Event created!', 'event': new_event.to_fc_event()}), 201
    except Exception as e: log.error(f"Error saving event: {e}", exc_info=True); return jsonify({'status': 'error', 'message': 'Failed to save.'}), 500

@main_routes.route('/calendar/event/<event_id>')
@login_required
def view_calendar_event(event_id):
    event = CalendarEvent.objects(pk=event_id, created_by=current_user).first_or_404()
    flash(f"Viewing details for event: {event.title} (Impl. Pending)", "info"); return redirect(url_for('main.project_calendar', project_id=event.project.id if event.project else None))

# --- CHAT ROUTES ---
@main_routes.route('/project/<project_id>/chat')
@login_required
def list_chat_groups(project_id):
    project = Project.objects(pk=project_id).first_or_404()
    groups = ChatGroup.objects(project=project).order_by('name')
    return render_template('chat/list_groups.html', title=f"{project.name} - Chat", project=project, groups=groups)

@main_routes.route('/project/<project_id>/chat/new', methods=['GET', 'POST'])
@login_required @admin_required
def create_chat_group(project_id):
    project = Project.objects(pk=project_id).first_or_404(); form = ChatGroupForm()
    if form.validate_on_submit():
        try:
            group = ChatGroup(name=form.name.data, project=project, created_by=current_user); group.save()
            flash(f"Chat group '{group.name}' created!", 'success'); return redirect(url_for('main.view_chat_group', project_id=project.id, group_id=group.id))
        except Exception as e: log.error(f"Chat group creation error: {e}", exc_info=True); flash("Error creating group.", 'danger')
    return render_template('chat/create_group.html', title='New Chat Group', form=form, project=project)

@main_routes.route('/project/<project_id>/chat/<group_id>', methods=['GET'])
@login_required
def view_chat_group(group_id, project_id): # Note: order matters if route matches project_id first
    project = Project.objects(pk=project_id).first_or_404()
    group = ChatGroup.objects(pk=group_id, project=project).first_or_404()
    messages = group.get_messages(limit=100).reverse(); message_form = ChatMessageForm()
    return render_template('chat/view_group.html', title=f"Chat: {group.name}", project=project, group=group, messages=messages, form=message_form)

@main_routes.route('/project/<project_id>/chat/<group_id>/message', methods=['POST'])
@login_required
def post_chat_message(project_id, group_id):
    # Ensure project/group exist and user has permission (simplified check here)
    group = ChatGroup.objects(pk=group_id, project=project_id).first()
    if not group: return jsonify({'status': 'error', 'message': 'Group not found or access denied.'}), 404
    form = ChatMessageForm() # Validate using WTForms CSRF
    if form.validate_on_submit():
        try:
            message = ChatMessage(group=group, sender=current_user, content=form.content.data); message.save()
            # TODO: Broadcast via WebSocket for real-time
            return jsonify({'status': 'success', 'message': 'Message sent.'}), 201 # Return minimal success for AJAX
        except Exception as e: log.error(f"Chat message post error: {e}", exc_info=True); return jsonify({'status': 'error', 'message': 'Failed to send.'}), 500
    else:
        errors = [e for field, errs in form.errors.items() for e in errs]
        return jsonify({'status': 'error', 'message': ". ".join(errors) or "Invalid input."}), 400

# --- Admin Routes ---
@main_routes.route('/admin')
@login_required @admin_required
def admin_console():
    counts = {'users': User.objects.count(), 'projects': Project.objects.count(), 'tasks': Task.objects.count()}
    return render_template('admin/console.html', title='Admin Console', **counts)

@main_routes.route('/admin/users')
@login_required @admin_required
def admin_list_users():
    users = User.objects.order_by('username'); return render_template('admin/users.html', title='Manage Users', users=users)

@main_routes.route('/admin/user/<user_id>/toggle_admin', methods=['POST'])
@login_required @admin_required
def admin_toggle_admin(user_id):
    user = User.objects(pk=user_id).first_or_404()
    if user == current_user and User.objects(is_admin=True).count() <= 1: flash('Cannot revoke self if only admin.', 'danger'); return redirect(url_for('main.admin_list_users'))
    try: user.is_admin = not user.is_admin; user.save(); status = "granted" if user.is_admin else "revoked"; flash(f'Admin {status} for {user.username}.', 'success')
    except Exception as e: log.error(f"Admin toggle error: {e}", exc_info=True); flash(f'Error updating status: {e}', 'danger')
    return redirect(url_for('main.admin_list_users'))

# --- Error Handlers ---
@main_routes.app_errorhandler(404)
def not_found_error(error): log.warning(f"404: {request.url}"); return render_template('errors/404.html'), 404
@main_routes.app_errorhandler(500)
def internal_error(error): log.error(f"500 Error: {request.url}", exc_info=error); return render_template('errors/500.html'), 500