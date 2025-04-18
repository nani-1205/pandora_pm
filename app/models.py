# app/models.py
# --- Import extensions ---
from .extensions import db, bcrypt
# --- Other imports ---
from flask_login import UserMixin
from flask import url_for # Needed for to_fc_event method
import datetime

# Define choices for task status
TASK_STATUS_CHOICES = ('To Do', 'In Progress', 'Blocked', 'In Review', 'Done')

# --- Theme Configuration ---
AVAILABLE_THEMES = [
    'pandora', 'amethyst_moon', 'frost_crystal', 'noir_flow', 'kernel_mindset'
]
DEFAULT_THEME = AVAILABLE_THEMES[0]
def format_theme_name(theme_id): return theme_id.replace('_', ' ').title()
THEME_CHOICES = [(theme_id, format_theme_name(theme_id)) for theme_id in AVAILABLE_THEMES]
# --- End Theme Configuration ---


# --- User Model ---
class User(db.Document, UserMixin):
    """Represents a user in the application."""
    email = db.EmailField(required=True, unique=True, max_length=100)
    username = db.StringField(required=True, unique=True, max_length=50)
    password_hash = db.StringField(required=True)
    is_admin = db.BooleanField(default=False)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    theme = db.StringField(choices=AVAILABLE_THEMES, default=DEFAULT_THEME, required=True)

    meta = {
        'indexes': [
            'email', # Index for login lookup
            'username' # Index for uniqueness check
        ]
    }

    def set_password(self, password):
        """Hashes the password and stores it."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', Admin: {self.is_admin})"

# --- Project Model ---
class Project(db.Document):
    """Represents a project."""
    name = db.StringField(required=True, max_length=120)
    description = db.StringField()
    created_by = db.ReferenceField(User, required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        'indexes': [
            'name', # Index for name lookup/uniqueness if needed
            'created_by' # Index for finding projects by user
        ]
    }

    def __repr__(self):
        return f"Project('{self.name}')"

# --- WorkPackage Model ---
class WorkPackage(db.Document):
    """Represents a logical grouping of tasks within a project."""
    name = db.StringField(required=True, max_length=150)
    description = db.StringField()
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
    created_by = db.ReferenceField(User, required=True)
    start_date = db.DateTimeField(null=True, blank=True) # Optional start date
    end_date = db.DateTimeField(null=True, blank=True)   # Optional end date
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        'indexes': [
            'project', # Index for finding WPs by project
            ('project', 'name') # Compound index for project-specific name lookup
        ]
    }

    def __repr__(self):
        return f"WorkPackage('{self.name}', Project: '{self.project.name}')"

# --- Milestone Model ---
class Milestone(db.Document):
    """Represents a significant point or goal in a project timeline."""
    name = db.StringField(required=True, max_length=150)
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
    target_date = db.DateTimeField(required=True)
    description = db.StringField(null=True, blank=True)
    created_by = db.ReferenceField(User, required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    # Corrected index syntax
    meta = {
        'indexes': [
            # Index milestones within a project, sorted newest target date first
            ('project', '-target_date')
        ]
    }

    def __repr__(self):
        return f"Milestone('{self.name}', Project: '{self.project.name}', Target: {self.target_date})"


# --- Task Model ---
class Task(db.Document):
    """Represents an individual task within a project."""
    title = db.StringField(required=True, max_length=200)
    description = db.StringField()
    status = db.StringField(choices=TASK_STATUS_CHOICES, default='To Do', required=True)
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
    work_package = db.ReferenceField(WorkPackage, null=True, blank=True, reverse_delete_rule=db.NULLIFY)
    assigned_to = db.ReferenceField(User, required=True, reverse_delete_rule=db.NULLIFY)
    created_by = db.ReferenceField(User, required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    due_date = db.DateTimeField(null=True, blank=True)

    meta = {
        'indexes': [
            'project',          # Find tasks by project
            'assigned_to',      # Find tasks by assignee
            ('project', 'status'), # Find tasks by status within a project
            ('project', 'work_package'), # Find tasks by WP within a project
            ('assigned_to', 'status'), # Find tasks by status for a user (for dashboard)
            ('assigned_to', 'due_date') # Find tasks by due date for a user
        ]
    }

    def __repr__(self):
        wp_name = f", WP: '{self.work_package.name}'" if self.work_package else ""
        return f"Task('{self.title}', Status: '{self.status}', Project: '{self.project.name}'{wp_name})"

# --- CalendarEvent Model ---
class CalendarEvent(db.Document):
    """Represents custom events created directly on the calendar."""
    title = db.StringField(required=True, max_length=200)
    description = db.StringField(null=True, blank=True)
    start_time = db.DateTimeField(required=True)
    end_time = db.DateTimeField(required=True)
    all_day = db.BooleanField(default=False)
    created_by = db.ReferenceField(User, required=True)
    project = db.ReferenceField(Project, null=True, blank=True, reverse_delete_rule=db.CASCADE) # Optional link to project
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        'indexes': [
            'project',
            'created_by',
            ('start_time', -1),
            ('project', 'start_time')
        ]
    }

    def __repr__(self):
        proj_name = f", Project: '{self.project.name}'" if self.project else ""
        return f"CalendarEvent('{self.title}', User: '{self.created_by.username}'{proj_name}, Start: {self.start_time})"

    # Method to convert to FullCalendar event object format
    def to_fc_event(self):
        """Converts this CalendarEvent object into a dict suitable for FullCalendar."""
        event_class = 'event-custom' # Specific class for styling

        # Ensure url_for generates URLs correctly within the application context
        # This might require the app context to be active when called.
        # Consider generating URLs in the route instead if context issues arise.
        try:
            event_url = url_for('main.view_calendar_event', event_id=self.id, _external=False)
        except RuntimeError: # Handle cases where url_for is called outside request context
            event_url = None # Or provide a default/placeholder URL
            # Log this issue if it occurs
            # current_app.logger.warning("Could not generate URL for CalendarEvent outside request context.")

        event_data = {
            'id': str(self.id), # Use the MongoDB ObjectId as ID
            'title': self.title,
            'start': self.start_time.isoformat(),
            'end': self.end_time.isoformat(),
            'allDay': self.all_day,
            'url': event_url, # Use generated URL or None
            'className': event_class,
            'extendedProps': {
                'type': 'custom_event',
                'description': self.description or '',
                'project': self.project.name if self.project else None,
                # Add other custom properties you might need in JS
            }
        }
        return event_data