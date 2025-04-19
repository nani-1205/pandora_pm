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

    meta = { 'indexes': [ 'email', 'username' ] }

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
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
    meta = { 'indexes': [ 'name', 'created_by' ] }
    def __repr__(self):
        return f"Project('{self.name}')"

# --- WorkPackage Model ---
class WorkPackage(db.Document):
    """Represents a logical grouping of tasks within a project."""
    name = db.StringField(required=True, max_length=150)
    description = db.StringField()
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
    created_by = db.ReferenceField(User, required=True)
    start_date = db.DateTimeField(null=True, blank=True)
    end_date = db.DateTimeField(null=True, blank=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    meta = { 'indexes': [ 'project', ('project', 'name') ] }
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
    meta = { 'indexes': [ ('project', '-target_date') ] }
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
    meta = { 'indexes': [ 'project', 'assigned_to', ('project', 'status'), ('project', 'work_package'), ('assigned_to', 'status'), ('assigned_to', 'due_date') ] }
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
    project = db.ReferenceField(Project, null=True, blank=True, reverse_delete_rule=db.CASCADE)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    meta = { 'indexes': [ 'project', 'created_by', '-start_time', ('project', '-start_time') ] }
    def __repr__(self):
        proj_name = f", Project: '{self.project.name}'" if self.project else ""
        return f"CalendarEvent('{self.title}', User: '{self.created_by.username}'{proj_name}, Start: {self.start_time})"

    def to_fc_event(self):
        event_class = 'event-custom'; event_url = None
        try: event_url = url_for('main.view_calendar_event', event_id=self.id, _external=False)
        except RuntimeError: pass
        return { 'id': str(self.id), 'title': self.title, 'start': self.start_time.isoformat(), 'end': self.end_time.isoformat(),
                 'allDay': self.all_day, 'url': event_url, 'className': event_class,
                 'extendedProps': { 'type': 'custom_event', 'description': self.description or '', 'project': self.project.name if self.project else None } }

# --- ChatGroup Model (NEW) ---
class ChatGroup(db.Document):
    """Represents a chat group associated with a project."""
    name = db.StringField(required=True, max_length=100)
    project = db.ReferenceField('Project', required=True, reverse_delete_rule=db.CASCADE)
    created_by = db.ReferenceField('User', required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    # members = db.ListField(db.ReferenceField('User')) # Optional: Explicit members later

    meta = {
        'indexes': [
            ('project', 'name') # Find groups by project and name
        ]
    }

    def get_messages(self, limit=50):
        """Helper to get recent messages for this group."""
        return ChatMessage.objects(group=self).order_by('-timestamp').limit(limit)

    def __repr__(self):
        return f"ChatGroup('{self.name}', Project: '{self.project.name}')"

# --- ChatMessage Model (NEW) ---
class ChatMessage(db.Document):
    """Represents a single message within a chat group."""
    group = db.ReferenceField('ChatGroup', required=True, reverse_delete_rule=db.CASCADE)
    sender = db.ReferenceField('User', required=True, reverse_delete_rule=db.NULLIFY) # Keep message if user deleted
    content = db.StringField(required=True)
    timestamp = db.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        'indexes': [
            ('group', '-timestamp') # Efficiently get latest messages for a group
        ]
    }

    def __repr__(self):
        sender_name = self.sender.username if self.sender else "[Deleted User]"
        return f"ChatMessage(Group: '{self.group.name}', Sender: '{sender_name}')"