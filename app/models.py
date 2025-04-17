# pandora_pm/app/models.py
from bson import ObjectId, errors as bson_errors
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .extensions import mongo, bcrypt
from datetime import datetime

# --- User Management ---

class User(UserMixin):
    """User model wrapper for Flask-Login."""
    def __init__(self, user_data):
        self.data = user_data

    @property
    def id(self):
        return str(self.data.get('_id'))

    @property
    def username(self):
        return self.data.get('username')

    @property
    def email(self):
        return self.data.get('email')

    @property
    def role(self):
        return self.data.get('role', 'user') # Default role

    @property
    def is_admin(self):
        return self.role == 'admin'

    def check_password(self, password):
        stored_hash = self.data.get('password_hash')
        if stored_hash:
            return bcrypt.check_password_hash(stored_hash, password)
        return False

    # Static methods for DB operations
    @staticmethod
    def find_by_username(username):
        return mongo.db.users.find_one({'username': username})

    @staticmethod
    def find_by_email(email):
        return mongo.db.users.find_one({'email': email})

    @staticmethod
    def get_by_id(user_id):
        try:
            user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if user_data:
                return User(user_data) # Return User object wrapper
        except (bson_errors.InvalidId, TypeError): # Handle invalid ObjectId format or None
            return None
        return None

    @staticmethod
    def create(username, email, password, role='user'):
        if User.find_by_username(username) or User.find_by_email(email):
            return None # User already exists

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user_doc = {
            'username': username,
            'email': email,
            'password_hash': hashed_password,
            'role': role,
            'created_at': datetime.utcnow()
        }
        try:
            result = mongo.db.users.insert_one(user_doc)
            return User.get_by_id(result.inserted_id)
        except Exception as e:
            print(f"Error creating user: {e}") # Log this properly
            return None

    @staticmethod
    def get_all_users():
        # Return sorted list of user dicts (or User objects if preferred)
        return list(mongo.db.users.find().sort('username', 1))

    @staticmethod
    def set_role(user_id, role):
         if role not in ['admin', 'user']:
             return False
         try:
             result = mongo.db.users.update_one(
                 {'_id': ObjectId(user_id)},
                 {'$set': {'role': role}}
             )
             return result.modified_count > 0
         except (bson_errors.InvalidId, TypeError):
             return False
         except Exception as e:
            print(f"Error setting user role: {e}") # Log this properly
            return False


# --- Project/Task Helpers ---

def create_project(name, description, owner_id, status="Not Started", due_date=None):
    try:
        project_doc = {
            'name': name,
            'description': description,
            'owner_id': ObjectId(owner_id),
            'status': status,
            'due_date': due_date, # Store as datetime object
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(), # Add updated_at on creation
            'tasks': [] # Embed tasks
        }
        result = mongo.db.projects.insert_one(project_doc)
        return str(result.inserted_id)
    except (bson_errors.InvalidId, TypeError):
        return None
    except Exception as e:
        print(f"Error creating project: {e}")
        return None

def get_project_by_id(project_id):
    try:
        return mongo.db.projects.find_one({'_id': ObjectId(project_id)})
    except (bson_errors.InvalidId, TypeError):
        return None

# === MODIFIED FUNCTION ===
def get_projects_for_user(user_id):
    """
    Finds projects where the user is the owner OR is assigned to any task within the project.
    Uses aggregation for efficiency.
    """
    try:
        user_obj_id = ObjectId(user_id) # Ensure user_id is an ObjectId

        pipeline = [
            {
                '$match': {
                    '$or': [
                        {'owner_id': user_obj_id}, # Condition 1: User owns the project
                        {'tasks.assigned_to': user_obj_id} # Condition 2: User is assigned to any task
                    ]
                }
            },
            {
                '$sort': {'created_at': -1} # Sort the results (optional)
            }
            # You could add a $project stage here if you need to reshape the output,
            # but for listing projects, returning the full document is usually fine.
        ]
        projects = list(mongo.db.projects.aggregate(pipeline))
        return projects
    except (bson_errors.InvalidId, TypeError):
        print(f"Error fetching projects: Invalid user ID format for '{user_id}'.")
        return []
    except Exception as e:
        print(f"Error fetching projects for user {user_id}: {e}")
        return []
# === END MODIFIED FUNCTION ===


def add_task_to_project(project_id, name, description, created_by_id, status="To Do", due_date=None, assigned_to_id=None): # Added assigned_to_id parameter
     try:
        task_doc = {
            '_id': ObjectId(), # Generate ID for the embedded task
            'project_id_ref': ObjectId(project_id), # Reference back to parent (optional but useful)
            'name': name,
            'description': description,
            'status': status,
            'due_date': due_date, # Store as datetime object
            'created_by': ObjectId(created_by_id),
            # Store assigned_to as ObjectId if provided, else store None
            'assigned_to': ObjectId(assigned_to_id) if assigned_to_id else None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow() # Add updated_at timestamp
        }
        result = mongo.db.projects.update_one(
            {'_id': ObjectId(project_id)},
            {'$push': {'tasks': task_doc}}
        )
        if result.modified_count > 0:
            return str(task_doc['_id']) # Return the new task's ID string
        else:
            return None # Project not found or not modified
     except (bson_errors.InvalidId, TypeError):
        print(f"Error adding task: Invalid ObjectId format for project '{project_id}' or user/assignee ID '{assigned_to_id}'.")
        return None
     except Exception as e:
        print(f"Error adding task: {e}")
        return None

def get_task_from_project(project_id, task_id):
    """Retrieve a specific embedded task."""
    try:
        project = mongo.db.projects.find_one(
            {'_id': ObjectId(project_id), 'tasks._id': ObjectId(task_id)},
            {'tasks.$': 1} # Projection to return only the matched task in the 'tasks' array
        )
        if project and 'tasks' in project and len(project['tasks']) == 1:
            return project['tasks'][0] # Return the task document (dict)
        return None
    except (bson_errors.InvalidId, TypeError):
        return None

def update_task_status_in_project(project_id, task_id, new_status):
    try:
        result = mongo.db.projects.update_one(
            # Match the project AND the specific task within the 'tasks' array
            {'_id': ObjectId(project_id), 'tasks._id': ObjectId(task_id)},
            # Use the positional '$' operator to update the matched array element
            {'$set': {'tasks.$.status': new_status, 'tasks.$.updated_at': datetime.utcnow()}}
        )
        return result.modified_count > 0
    except (bson_errors.InvalidId, TypeError):
        return False
    except Exception as e:
        print(f"Error updating task status: {e}")
        return False

def delete_task_from_project(project_id, task_id):
     try:
         result = mongo.db.projects.update_one(
             {'_id': ObjectId(project_id)},
             {'$pull': {'tasks': {'_id': ObjectId(task_id)}}} # Pull task by its ID
         )
         return result.modified_count > 0
     except (bson_errors.InvalidId, TypeError):
         return False
     except Exception as e:
        print(f"Error deleting task: {e}")
        return False

def delete_project(project_id):
    try:
        result = mongo.db.projects.delete_one({'_id': ObjectId(project_id)})
        return result.deleted_count > 0
    except (bson_errors.InvalidId, TypeError):
        return False
    except Exception as e:
        print(f"Error deleting project: {e}")
        return False

# --- HELPER: Get user dictionary ---
def get_user_dict():
    """Returns a dictionary mapping user IDs (str) to usernames."""
    users = User.get_all_users() # Fetches list of user dicts
    if users:
        return {str(user['_id']): user.get('username', 'Unknown') for user in users}
    return {}


# --- Update Task Function ---
def update_task_in_project(project_id, task_id, update_data):
    """Updates fields of an embedded task."""
    # Construct the $set update document prefixing fields with 'tasks.$.'
    set_update = {f'tasks.$.{key}': value for key, value in update_data.items()}
    # Always update the 'updated_at' field for the task
    set_update['tasks.$.updated_at'] = datetime.utcnow()

    # Convert assigned_to ID string back to ObjectId if present
    if 'assigned_to' in set_update:
        assignee_val = set_update['tasks.$.assigned_to'] # Get the value passed
        if assignee_val: # Check if it's a non-empty string
             try:
                 set_update['tasks.$.assigned_to'] = ObjectId(assignee_val)
             except (bson_errors.InvalidId, TypeError):
                 print(f"Error updating task: Invalid assigned_to ID format '{assignee_val}'.")
                 return False # Or handle error differently
        else:
            set_update['tasks.$.assigned_to'] = None # Set to null if empty string selected ("-- Unassigned --")

    # Convert due_date if present (it should already be datetime object from route)
    # No conversion usually needed here if route logic handles it

    try:
        result = mongo.db.projects.update_one(
            {'_id': ObjectId(project_id), 'tasks._id': ObjectId(task_id)},
            {'$set': set_update}
        )
        return result.modified_count >= 0 # Return True if matched, even if no fields changed
    except (bson_errors.InvalidId, TypeError):
        print("Error updating task: Invalid project or task ID format.")
        return False
    except Exception as e:
        print(f"Error updating task details: {e}")
        return False