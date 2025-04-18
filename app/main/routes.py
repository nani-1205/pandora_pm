from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from . import bp
from ..models import get_projects_for_user # Import helper

@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    """Displays the main dashboard for the logged-in user."""
    user_projects = get_projects_for_user(current_user.id)

    # TODO: Add logic to fetch tasks due soon, recent activity, etc.
    # Example: Fetch tasks assigned to user across all their projects (more complex query)
    # tasks_assigned = list(mongo.db.projects.find(
    #     {'owner_id': ObjectId(current_user.id), 'tasks.assigned_to': ObjectId(current_user.id)},
    #     {'tasks.$': 1} # This projection might need refinement depending on needs
    # ))

    return render_template('dashboard.html',
                           title='Dashboard',
                           projects=user_projects
                           # Pass other data like tasks_due_soon, stats etc.
                          )

# Add other general routes here (e.g., user profile page)
# @bp.route('/profile')
# @login_required
# def profile():
#     return render_template('profile.html', title='My Profile')