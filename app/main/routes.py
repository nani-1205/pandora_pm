# pandora_pm/app/main/routes.py
from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from . import bp
from ..models import get_projects_for_user
from ..extensions import mongo # For more complex dashboard queries if needed
from bson import ObjectId

# --- NEW: Route for the index/landing page ---
@bp.route('/')
def index():
    # Optional: If a user is already logged in, redirect them straight to the dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    # Otherwise, show the public landing page
    return render_template('index.html', title='Welcome')

# --- Dashboard route remains mostly the same ---
@bp.route('/dashboard')
@login_required
def dashboard():
    try:
        user_projects = get_projects_for_user(current_user.id)

        # Example: Fetch recent tasks across user's projects (adjust query as needed)
        # This gets tasks from projects the user OWNS. Modify if 'assigned' tasks are needed.
        pipeline = [
            {'$match': {'owner_id': ObjectId(current_user.id)}}, # Match projects owned by user
            {'$unwind': '$tasks'}, # Deconstruct the tasks array
            {'$match': {'tasks.status': {'$ne': 'Done'}}}, # Filter out completed tasks (example)
            {'$sort': {'tasks.due_date': 1, 'tasks.created_at': -1}}, # Sort by due date, then creation
            {'$limit': 10}, # Limit to 10 tasks for the dashboard
            {'$project': { # Reshape the output
                '_id': 0, # Exclude the default project _id unless needed
                'project_id': '$_id', # Rename project's _id
                'project_name': '$name',
                'task_id': '$tasks._id',
                'task_name': '$tasks.name',
                'task_status': '$tasks.status',
                'task_due_date': '$tasks.due_date'
            }}
        ]
        upcoming_tasks = list(mongo.db.projects.aggregate(pipeline))

    except Exception as e:
        flash('Error loading dashboard data.', 'danger')
        print(f"Dashboard Error: {e}") # Log this properly in production
        user_projects = []
        upcoming_tasks = []

    return render_template('dashboard.html',
                           title='Dashboard',
                           projects=user_projects,
                           tasks=upcoming_tasks) # Pass tasks to the dashboard template