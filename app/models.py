# app/models.py
# --- Import extensions ---
from .extensions import db, bcrypt
# ---, along with the other models and theme configuration.

```python
# app/ Other imports ---
from flask_login import UserMixin
from flask import url_for # Needed for to_fc_event method
import datetime

# Definemodels.py
# --- Import extensions ---
from .extensions import db, bcrypt
# --- Other imports ---
from flask_login import UserMixin
 choices for task status
TASK_STATUS_CHOICES = ('To Do', 'In Progress', 'Blocked', 'In Review', 'Done')

#from flask import url_for # Needed for to_fc_event method
import datetime

# Define choices for task status
TASK_STATUS_CHOICES = --- Theme Configuration ---
AVAILABLE_THEMES = [
    'pandora', 'amethyst_moon', 'frost_crystal', 'noir_flow', 'kernel_mindset'
]
DEFAULT_THEME = AVAILABLE_THEMES[0]
def format_theme_name(theme_ ('To Do', 'In Progress', 'Blocked', 'In Review', 'Done')

# --- Theme Configuration ---
AVAILABLE_THEMES = [
    'pandora', 'amethyst_moon', 'frost_crystal', 'noir_flow', 'kernel_mindset'
]
DEFAULT_THEME = AVAILABLE_THEMES[0]
def format_theme_id): return theme_id.replace('_', ' ').title()
THEME_CHOICES = [(theme_id, format_theme_name(theme_id)) for theme_id in AVAILABLE_THEMES]
#name(theme_id): return theme_id.replace('_', ' '). --- End Theme Configuration ---


# --- User Model ---
class User(db.Document, UserMixin):
    """Represents a user in the applicationtitle()
THEME_CHOICES = [(theme_id, format_theme_name(theme_id)) for theme_id in AVAILABLE_THE."""
    email = db.EmailField(required=True, unique=True, max_length=100)
    username = db.MES]
# --- End Theme Configuration ---


# --- User Model ---
class User(db.Document, UserMixin):
    """Represents a user in the application."""
    email = db.EmailField(required=StringField(required=True, unique=True, max_length=50)
    password_hash = db.StringField(required=True)
    is_admin = db.BooleanField(default=False)
True, unique=True, max_length=100)
    username = db.StringField(required=True, unique=True, max_length=50)
    password_hash = db.StringField(required=True)
    is_admin = db.BooleanField(default    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    theme = db.StringField(choices=AVAILABLE_THEMES, default=DEFAULT_THEME, required=True)

    meta ==False)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    theme = db.StringField(choices=AVAILABLE_THEMES, default=DEFAULT_THEME, required=True) {
        'indexes': [
            'email', # Index for login lookup
            'username' # Index for uniqueness check
        ]
    }

    def set_password(self, password):
        """Hashes the

    meta = {
        'indexes': [
            'email', # Index for login lookup
            'username' # Index for uniqueness check
        ]
    }

    def set_password(self, password):
        """Hashes the password and stores it."""
        self.password password and stores it."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        return bcrypt.check_password_hash(_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        return bcrypt.self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', Admin: {self.is_admin})"

# --- Project Model ---
class Projectcheck_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', Admin: {self.is_admin})"

# --- Project Model ---
class Project(db.Document):
    """Represents a(db.Document):
    """Represents a project."""
    name = db.StringField(required=True, max_length=120)
    description = db.StringField()
    created_by = db.ReferenceField(User, required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

     project."""
    name = db.StringField(required=True, max_length=120)
    description = db.StringField()
    created_by = db.ReferenceField(User, required=Truemeta = {
        'indexes': [
            'name', # Index for name lookup/uniqueness if needed
            'created_by' # Index for finding projects by user
        ]
    }

    def __repr__()
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        'indexes': [
            'name', # Index for name lookup/uniqueness if needed
            'created_by' # Index for finding projects by user
        ]
    self):
        return f"Project('{self.name}')"

# --- WorkPackage Model ---
class WorkPackage(db.Document):
    """Represents a logical grouping of tasks within a project."""
    name = db.StringField(required=True, max_length=150}

    def __repr__(self):
        return f"Project('{self.name}')"

# --- WorkPackage Model ---
class WorkPackage(db.Document):
    """Represents a logical grouping of tasks within a project."""
    name = db.StringField(required=True, max_length=150)
    description = db.StringField)
    description = db.StringField()
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
    created_by = db.ReferenceField(User, required=True)
    start_date = db.DateTimeField(null=()
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
    created_by = db.ReferenceField(User, required=True)
    start_dateTrue, blank=True) # Optional start date
    end_date = db.DateTimeField(null=True, blank=True)   # Optional end date
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        'indexes': [
             = db.DateTimeField(null=True, blank=True) # Optional start date
    end_date = db.DateTimeField(null=True, blank=True)   # Optional end date
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        'indexes': [
            'project', # Index for finding WPs by project
'project', # Index for finding WPs by project
            ('project', 'name') # Compound index for project-specific name lookup
        ]
    }

    def __repr__(self):
        return f"WorkPackage('{self.name}', Project: '{self.project.name}')"            ('project', 'name') # Compound index for project-specific name lookup
        ]
    }

    def __repr__(self):
        return f"WorkPackage('{self.name}', Project: '{self.project.name}')"

# --- Milestone Model ---
class Milestone(db.

# --- Milestone Model ---
class Milestone(db.Document):
    """Represents a significant point or goal in a project timeline."""
    name = db.StringField(required=True, max_length=150)
    project = db.ReferenceField(Project, required=TrueDocument):
    """Represents a significant point or goal in a project timeline."""
    name = db.StringField(required=True, max_length=150)
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
, reverse_delete_rule=db.CASCADE)
    target_date = db.DateTimeField(required=True)
    description = db.StringField(null=True, blank=True)
    created_by =    target_date = db.DateTimeField(required=True)
    description = db.StringField(null=True, blank=True)
     db.ReferenceField(User, required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    # Corrected index syntax using string prefix for descending
    meta = {
        'indexes':created_by = db.ReferenceField(User, required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    # Corrected index syntax using explicit compound index
    meta = {
         [
            ('project', '-target_date') # Compound index on project, then target_date descending
        ]
    }

    def __repr__(self'indexes': [
            # Index milestones within a project, sorted newest target date first
            ('project', '-target_date')
        ]
    }

    def __repr__(self):
        return f"Milestone('{self):
        return f"Milestone('{self.name}', Project: '{self.project.name}', Target: {self.target_date})"


# --- Task Model ---
class Task(db.Document):
    """Represents an individual task within a project."""
    title = db.String.name}', Project: '{self.project.name}', Target: {self.target_date})"


# --- Task Model ---
class Task(db.Document):
    """Represents an individual task within a project."""
Field(required=True, max_length=200)
    description = db.StringField()
    status = db.StringField(choices=TASK_STATUS_CHOICES, default='To Do', required=True)
    title = db.StringField(required=True, max_length=200)
    description = db.StringField()
    status = db.StringField(choices=TASK_STATUS_CHOICES, default    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
    work_package = db.ReferenceField(WorkPackage, null=True, blank=True, reverse_='To Do', required=True)
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
    work_package = db.ReferenceField(WorkPackage, null=True,delete_rule=db.NULLIFY)
    assigned_to = db blank=True, reverse_delete_rule=db.NULLIFY)
    assigned_to = db.ReferenceField(User, required=True,.ReferenceField(User, required=True, reverse_delete_rule=db.NULLIFY)
    created_by = db.ReferenceField(User, required=True)
    created_at = db.DateTimeField( reverse_delete_rule=db.NULLIFY)
    created_bydefault=datetime.datetime.utcnow)
    due_date = db. = db.ReferenceField(User, required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    DateTimeField(null=True, blank=True)

    meta = {
        'indexes': [
            'project',          # Find tasks by project
            'assigned_to',      # Find tasks by assignee
            ('project', 'due_date = db.DateTimeField(null=True, blank=True)

    meta = {
        'indexes': [
            'project',          # Find tasks by project
            'assigned_to',      # Find tasks bystatus'), # Find tasks by status within a project
            ('project', 'work_package'), # Find tasks by WP within a project
            ('assigned assignee
            ('project', 'status'), # Find tasks by status within a project
            ('project', 'work_package'), # Find tasks by WP_to', 'status'), # Find tasks by status for a user (for dashboard)
            ('assigned_to', 'due_date') # Find tasks by due date for a user
        ]
    }

    def within a project
            ('assigned_to', 'status'), # Find tasks by status for a user (for dashboard)
            ('assigned_to', 'due_date') # Find tasks by due date for a user
         __repr__(self):
        wp_name = f", WP: '{self.work_package.name}'" if self.work_package else ""
        return f"Task('{self.title}', Status: '{self]
    }

    def __repr__(self):
        wp_name = f", WP: '{self.work_package.name}'".status}', Project: '{self.project.name}'{wp_name})"

# --- CalendarEvent Model ---
class CalendarEvent(db.Document if self.work_package else ""
        return f"Task('{self.title}', Status: '{self.status}', Project: '{self.project.name}'{wp_name})"

# --- CalendarEvent Model ---
class CalendarEvent):
    """Represents custom events created directly on the calendar."""
    title = db.StringField(required=True, max_length=2(db.Document):
    """Represents custom events created directly on the calendar."""
    title = db.StringField(required=True, max00)
    description = db.StringField(null=True, blank=True)
    start_time = db.DateTimeField(required=True)
    end_time = db.DateTimeField(required=True)
    all_day = db.BooleanField(default=False)
    _length=200)
    description = db.StringField(null=True, blank=True)
    start_time = db.DateTimeField(required=True)
    end_time = db.DateTimeField(required=True)
    all_day = db.BooleanField(default=created_by = db.ReferenceField(User, required=True)
    project = db.ReferenceField(Project, null=True, blank=True, reverse_delete_rule=db.CASCADE) # Optional link toFalse)
    created_by = db.ReferenceField(User, required=True)
    project = db.ReferenceField(Project, null=True, blank=True, reverse_delete_rule=db.CASCADE) project
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    # Corrected index syntax using string prefix for descending
    meta = {
        'indexes': [
            'project',
 # Optional link to project
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    # Corrected index syntax using explicit            'created_by',
            '-start_time', # Index descending compound index
    meta = {
        'indexes': [
            'project',
            'created_by',
            '-start_time', by start time
            ('project', '-start_time') # Compound index on project, then start time descending
        ]
    }

    def __repr__( # Simple descending index on start time
            ('project', '-start_time') # Compound index for project-specific time sorting
        ]
    }

self):
        proj_name = f", Project: '{self.project.name}'" if self.project else ""
        return f"Calendar    def __repr__(self):
        proj_name = f", ProjectEvent('{self.title}', User: '{self.created_by.username}': '{self.project.name}'" if self.project else ""
        return f"CalendarEvent('{self.title}', User: '{self.{proj_name}, Start: {self.start_time})"

    # Method to convert to FullCalendar event object format
    def to_fc_event(self):
        """Converts this CalendarEvent object into a dict suitable forcreated_by.username}'{proj_name}, Start: {self.start_time})"

    # Method to convert to FullCalendar event object format
    def to_fc_event(self):
        """Converts this Calendar FullCalendar."""
        event_class = 'event-custom' # Specific class for styling
        event_url = None
        try:
            # Generate URL only if withinEvent object into a dict suitable for FullCalendar."""
        event_class = 'event-custom' # Specific class for styling

        # Generate URL within the application a request context
            event_url = url_for('main.view_calendar_event', event_id=self.id, _external=False) context if possible
        try:
            # Ensure Flask-Login's current_user
        except RuntimeError:
            # Log or handle the case where url_for proxy is available if needed indirectly by url_for
            # Typically url_for doesn cannot be called
            pass # event_url remains None

        event_data = {'t directly need current_user for basic route generation
            event_url = url_for('main.view_calendar_event', event_id=
            'id': str(self.id), # Use the MongoDB ObjectId as ID
            'title': self.title,
            'start': self.start_time.isoformat(),
            'end': self.end_time.isoformat(),
            'allDay': self.all_day,self.id, _external=False)
        except RuntimeError: # Handle cases where url_for is called outside request/app context
            event_url = None #
            'url': event_url, # Use generated URL or None
            'className': event_class,
            'extendedProps': {
 Provide a default/placeholder URL or None
            # Consider logging this situation if it                'type': 'custom_event',
                'description': self.description or '',
                'project': self.project.name if self.project else None,
            }
        }
        return event_data