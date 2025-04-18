# app/models.py
from .extensions import db, bcrypt # Import from extensions
from flask_login import UserMixin
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
    email = db.EmailField(required=True, unique=True, max_length=100)
    username = db.StringField(required=True, unique=True, max_length=50)
    password_hash = db.StringField(required=True)
    is_admin = db.BooleanField(default=False)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    theme = db.StringField(choices=AVAILABLE_THEMES, default=DEFAULT_THEME, required=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', Admin: {self.is_admin})"

# --- Project Model ---
class Project(db.Document):
    name = db.StringField(required=True, max_length=120)
    description = db.StringField()
    created_by = db.ReferenceField(User, required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    meta = {'indexes': ['name']}
    def __repr__(self):
        return f"Project('{self.name}')"

# --- WorkPackage Model (NEW) ---
class WorkPackage(db.Document):
    name = db.StringField(required=True, max_length=150)
    description = db.StringField()
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
    created_by = db.ReferenceField(User, required=True)
    start_date = db.DateTimeField(null=True, blank=True) # Optional start date
    end_date = db.DateTimeField(null=True, blank=True)   # Optional end date
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    meta = {'indexes': ['project', 'name']}

    def __repr__(self):
        return f"WorkPackage('{self.name}', Project: '{self.project.name}')"

# --- Milestone Model (NEW) ---
class Milestone(db.Document):
    name = db.StringField(required=True, max_length=150)
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
    target_date = db.DateTimeField(required=True)
    description = db.StringField(null=True, blank=True)
    created_by = db.ReferenceField(User, required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    meta = {'indexes': ['project', ('target_date', -1)]} # Index by project and date descending

    def __repr__(self):
        return f"Milestone('{self.name}', Project: '{self.project.name}', Target: {self.target_date})"


# --- Task Model (UPDATED) ---
class Task(db.Document):
    title = db.StringField(required=True, max_length=200)
    description = db.StringField()
    status = db.StringField(choices=TASK_STATUS_CHOICES, default='To Do', required=True)
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE)
    # --- NEW: Optional link to WorkPackage ---
    work_package = db.ReferenceField(WorkPackage, null=True, blank=True, reverse_delete_rule=db.NULLIFY)
    assigned_to = db.ReferenceField(User, required=True, reverse_delete_rule=db.NULLIFY)
    created_by = db.ReferenceField(User, required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    due_date = db.DateTimeField(null=True, blank=True)
    meta = {'indexes': ['project', 'assigned_to', 'status', 'work_package']} # Add index for WP

    def __repr__(self):
        wp_name = f", WP: '{self.work_package.name}'" if self.work_package else ""
        return f"Task('{self.title}', Status: '{self.status}', Project: '{self.project.name}'{wp_name})"