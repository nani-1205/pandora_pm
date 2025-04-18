# app/models.py
from . import db, bcrypt
from flask_login import UserMixin
import datetime

# Define choices for task status
TASK_STATUS_CHOICES = ('To Do', 'In Progress', 'Blocked', 'In Review', 'Done')

class User(db.Document, UserMixin):
    email = db.EmailField(required=True, unique=True, max_length=100)
    username = db.StringField(required=True, unique=True, max_length=50)
    password_hash = db.StringField(required=True)
    is_admin = db.BooleanField(default=False)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

    # Flask-Login integration: The `id` property is automatically handled by MongoEngine's pk (primary key)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', Admin: {self.is_admin})"

class Project(db.Document):
    name = db.StringField(required=True, max_length=120)
    description = db.StringField()
    created_by = db.ReferenceField(User, required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    # Removed members list - task assignment implies membership for now.
    # Add back if project-level permissions are needed later.

    meta = {'indexes': ['name']} # Add index for faster name lookups

    def __repr__(self):
        return f"Project('{self.name}')"

class Task(db.Document):
    title = db.StringField(required=True, max_length=200)
    description = db.StringField()
    status = db.StringField(choices=TASK_STATUS_CHOICES, default='To Do', required=True)
    project = db.ReferenceField(Project, required=True, reverse_delete_rule=db.CASCADE) # Cascade delete tasks if project is deleted
    assigned_to = db.ReferenceField(User, required=True, reverse_delete_rule=db.NULLIFY) # Keep task if user is deleted, but unassign
    created_by = db.ReferenceField(User, required=True) # Who created the task (usually admin)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    due_date = db.DateTimeField(null=True, blank=True) # Optional due date

    meta = {'indexes': ['project', 'assigned_to', 'status']} # Indexes for common queries

    def __repr__(self):
        return f"Task('{self.title}', Status: '{self.status}', Project: '{self.project.name}')"