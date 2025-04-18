# pandora_pm/app/models.py
from bson import ObjectId
from flask_login import UserMixin
from .extensions import mongo, bcrypt
from datetime import datetime
import pytz # Recommended for timezone handling if needed

# --- User Management ---

class User(UserMixin):
    """
    User model wrapper for Flask-Login.
    Interacts with the 'users' collection in MongoDB.
    """
    def __init__(self, user_data):
        """
        Initializes User object from MongoDB document (dictionary).
        """
        if not isinstance(user_data, dict):
             raise TypeError("user_data must be a dictionary from MongoDB")
        self.data = user_data

    @property
    def id(self):
        """Required by Flask-Login. Returns user's MongoDB ObjectId as string."""
        return str(self.data.get('_id'))

    @property
    def username(self):
        return self.data.get('username')

    @property
    def email(self):
        return self.data.get('email')

    @property
    def role(self):
        # Ensure a default role if not present
        return self.data.get('role', 'user')

    @property
    def password_hash(self):
         return self.data.get('password_hash')

    @property
    def created_at(self):
         # Return timezone-aware datetime if stored, otherwise naive UTC
         dt = self.data.get('created_at')
         # Could add timezone conversion here if needed
         return dt

    @property
    def is_admin(self):
        return self.role == 'admin'

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        pw_hash = self.password_hash
        if not pw_hash:
            return False
        return bcrypt.check_password_hash(pw_hash, password)

    # --- Static methods for DB operations ---
    @staticmethod
    def get_collection():
        """Helper to get the users collection."""
        return mongo.db.users

    @staticmethod
    def find_by_username(username):
        """Finds a user document by username."""
        return User.get_collection().find_one({'username': username})

    @staticmethod
    def find_by_email(email):
        """Finds a user document by email."""
        return User.get_collection().find_one({'email': email})

    @staticmethod
    def get_by_id(user_id):
        """Finds a user by MongoDB ObjectId string and returns a User object."""
        try:
            user_data = User.get_collection().find_one({'_id': ObjectId(user_id)})
            if user_data:
                return User(user_data) # Return the wrapper object
        except Exception: # Handle invalid ObjectId format gracefully
            return None
        return None

    @staticmethod
    def create(username, email, password, role='user'):
        """Creates a new user in the database. Returns User object or None."""
        if User.find_by_username(username) or User.find_by_email(email):
            print(f"Attempt to create existing user: {username} / {email}")
            return None # User already exists

        try:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user_doc = {
                'username': username,
                'email': email.lower(), # Store email in lowercase for consistency
                'password_hash': hashed_password,
                'role': role,
                'created_at': datetime.utcnow() # Store in UTC
            }
            result = User.get_collection().insert_one(user_doc)
            print(f"User created with ID: {result.inserted_id}")
            return User.get_by_id(result.inserted_id)
        except Exception as e:
            print(f"Error creating user {username}: {e}")
            # Log the error properly in a real application
            return None


    @staticmethod
    def get_all_users():
        """Retrieves all user documents."""
        return list(User.get_collection().find().sort('username', 1))


    @staticmethod
    def update_role(user_id, new_role):
        """Updates the role for a given user ID."""
        if new_role not in ['user', 'admin']:
            return False # Invalid role
        try:
            result = User.get_collection().update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'role': new_role}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating role for user {user_id}: {e}")
            return False

# --- Project/Task DB Helpers ---

def get_projects_collection():
    return mongo.db.projects

# We are embedding tasks, so no separate tasks collection needed for this example

def create_project(name, description, owner_id, status="Not Started", due_date=None):
    """Creates a new project document."""
    if not name or not owner_id:
        return None # Basic validation
    try:
        project_doc = {
            'name': name,
            'description': description,
            'owner_id': ObjectId(owner_id), # Reference to the user who owns it
            'status': status, # e.g., "Not Started", "In Progress", "Completed", "On Hold"
            'due_date': due_date, # Store as datetime object if provided
            'created_at': datetime.utcnow(),
            'last_updated': datetime.utcnow(),
            'tasks': [] # Embed tasks as a list of sub-documents
            # Could add 'members': [ObjectId(user_id1), ObjectId(user_id2)] later
        }
        result = get_projects_collection().insert_one(project_doc)
        return result.inserted_id
    except Exception as e:
        print(f"Error creating project {name}: {e}")
        return None


def get_project_by_id(project_id):
    """Retrieves a project document by its ID."""
    try:
        return get_projects_collection().find_one({'_id': ObjectId(project_id)})
    except Exception:
        return None


def get_projects_for_user(user_id):
    """Finds projects owned by the user. Expand later for assigned projects."""
    try:
        # Simple query for owned projects, sorted by most recently created
        return list(get_projects_collection().find(
            {'owner_id': ObjectId(user_id)}
        ).sort('created_at', -1))
    except Exception as e:
        print(f"Error fetching projects for user {user_id}: {e}")
        return []


def add_task_to_project(project_id, name, description, created_by_id, status="To Do", due_date=None, assigned_to_id=None):
    """Adds a task sub-document to a project."""
    if not name or not project_id or not created_by_id:
        return None
    try:
        task_id = ObjectId() # Generate a unique ID for the embedded task
        task_doc = {
            '_id': task_id,
            'name': name,
            'description': description,
            'status': status, # e.g., "To Do", "In Progress", "Done", "Blocked"
            'due_date': due_date,
            'created_by': ObjectId(created_by_id),
            'assigned_to': ObjectId(assigned_to_id) if assigned_to_id else None,
            'created_at': datetime.utcnow(),
            'last_updated': datetime.utcnow()
        }
        result = get_projects_collection().update_one(
            {'_id': ObjectId(project_id)},
            {
                '$push': {'tasks': task_doc},
                '$set': {'last_updated': datetime.utcnow()} # Update project timestamp
            }
        )
        return task_id if result.modified_count > 0 else None
    except Exception as e:
        print(f"Error adding task to project {project_id}: {e}")
        return None


def get_task_from_project(project_id, task_id):
    """Retrieves a specific embedded task document."""
    try:
        project = get_projects_collection().find_one(
            {'_id': ObjectId(project_id), 'tasks._id': ObjectId(task_id)},
            {'tasks.$': 1} # Projection to return only the matched task
        )
        if project and 'tasks' in project and project['tasks']:
            return project['tasks'][0] # Return the task sub-document
    except Exception as e:
        print(f"Error getting task {task_id} from project {project_id}: {e}")
    return None


def update_task_status_in_project(project_id, task_id, new_status):
    """Updates the status of an embedded task."""
    try:
        result = get_projects_collection().update_one(
            {'_id': ObjectId(project_id), 'tasks._id': ObjectId(task_id)},
            {'$set': {
                'tasks.$.status': new_status,
                'tasks.$.last_updated': datetime.utcnow(),
                'last_updated': datetime.utcnow() # Update project timestamp too
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating status for task {task_id} in project {project_id}: {e}")
        return False

# --- Add functions for updating/deleting projects and tasks as needed ---
# Example: Delete Project
def delete_project_by_id(project_id):
    try:
        result = get_projects_collection().delete_one({'_id': ObjectId(project_id)})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting project {project_id}: {e}")
        return False

# Example: Delete Task (pull from embedded array)
def delete_task_from_project(project_id, task_id):
     try:
         result = get_projects_collection().update_one(
             {'_id': ObjectId(project_id)},
             {'$pull': {'tasks': {'_id': ObjectId(task_id)}},
              '$set': {'last_updated': datetime.utcnow()}
             }
         )
         return result.modified_count > 0
     except Exception as e:
         print(f"Error deleting task {task_id} from project {project_id}: {e}")
         return False