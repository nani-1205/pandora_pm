# pandora_pm/app/main/routes.py
from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from . import bp
from ..models import get_projects_for_user # Use the updated function
from ..extensions import mongo # For more complex dashboard queries if needed
from bson import ObjectId

@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html', title='Welcome')

@bp.route('/dashboard')
@login_required
def dashboard():
    # print(f"\n--- main.dashboard: ENTERING ROUTE ---") # Debug
    user_projects = []
    upcoming_tasks = []
    try:
        current_user_id = current_user.id
        # print(f"--- main.dashboard: current_user.id = '{current_user_id}', type = {type(current_user_id)} ---") # Debug

        user_projects = get_projects_for_user(current_user_id) # Fetch projects user has access to

        # Fetch upcoming tasks assigned to the user
        pipeline = [
            {'$unwind': '$tasks'}, # Deconstruct the tasks array first
            {'$match': {
                'tasks.assigned_to': ObjectId(current_user_id), # Match tasks assigned to user
                'tasks.status': {'$ne': 'Done'} # Filter out completed tasks
            }},
            {'$sort': {'tasks.due_date': 1, 'tasks.created_at': -1}},
            {'$limit': 10},
            {'$project': { # Reshape for display
                '_id': 0,
                'project_id': '$_id', # Project ID from root document
                'project_name': '$name', # Project name from root document
                'task_id': '$tasks._id',
                'task_name': '$tasks.name',
                'task_status': '$tasks.status',
                'task_due_date': '$tasks.due_date'
            }}
        ]
        # print(f"--- main.dashboard: Fetching upcoming tasks for user ObjectId: {ObjectId(current_user_id)} ---") # Debug
        upcoming_tasks = list(mongo.db.projects.aggregate(pipeline))
        # print(f"--- main.dashboard: Found {len(upcoming_tasks)} upcoming tasks ---") # Debug

    except Exception as e:
        flash('Error loading dashboard data.', 'danger')
        print(f"--- main.dashboard: ERROR loading data: {e} ---")
        # Ensure variables are still lists on error
        user_projects = []
        upcoming_tasks = []

    # print(f"--- main.dashboard: EXITING ROUTE (Rendering template with {len(user_projects)} projects) ---") # Debug
    return render_template('dashboard.html',
                           title='Dashboard',
                           projects=user_projects,
                           tasks=upcoming_tasks)