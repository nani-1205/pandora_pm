# pandora_pm/app/main/routes.py
from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from . import bp
from ..models import get_projects_for_user # Use the updated function
from ..extensions import mongo # For more complex dashboard queries if needed
from bson import ObjectId

@bp.route('/')
def index():
    # Optional: If a user is already logged in, redirect them straight to the dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    # Otherwise, show the public landing page
    return render_template('index.html', title='Welcome')

@bp.route('/dashboard')
@login_required
def dashboard():
    try:
        # Fetch projects user has access to (using the updated model function)
        user_projects = get_projects_for_user(current_user.id)

        # === MODIFIED PIPELINE FOR UPCOMING TASKS ===
        # Fetch tasks ASSIGNED to the current user across projects they have access to
        pipeline = [
            # Match documents where the tasks array contains at least one task assigned to the user
            # This first match isn't strictly necessary anymore if get_projects_for_user works,
            # but helps narrow down initial documents if needed. Can be removed for simplicity.
            # {'$match': {'tasks.assigned_to': ObjectId(current_user.id)}},
            {'$unwind': '$tasks'}, # Deconstruct the tasks array
            # Now filter specifically for tasks assigned to the current user AND not done
            {'$match': {
                'tasks.assigned_to': ObjectId(current_user.id),
                'tasks.status': {'$ne': 'Done'} # Filter out completed tasks
            }},
            {'$sort': {'tasks.due_date': 1, 'tasks.created_at': -1}}, # Sort by due date, then creation
            {'$limit': 10}, # Limit to 10 tasks for the dashboard
            {'$project': { # Reshape the output
                '_id': 0, # Exclude the default project _id
                'project_id': '$_id', # Use the root document's _id as project_id
                'project_name': '$name', # Get project name from root document
                'task_id': '$tasks._id',
                'task_name': '$tasks.name',
                'task_status': '$tasks.status',
                'task_due_date': '$tasks.due_date'
            }}
        ]
        upcoming_tasks = list(mongo.db.projects.aggregate(pipeline))
        # === END MODIFIED PIPELINE ===

    except Exception as e:
        flash('Error loading dashboard data.', 'danger')
        print(f"Dashboard Error: {e}") # Log this properly in production
        user_projects = []
        upcoming_tasks = []

    return render_template('dashboard.html',
                           title='Dashboard',
                           projects=user_projects, # List of projects user owns or is assigned to
                           tasks=upcoming_tasks) # List of tasks assigned to user