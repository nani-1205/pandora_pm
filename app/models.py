# pandora_pm/app/models.py
from bson import ObjectId
from flask_login import UserMixin
from .extensions import mongo, bcrypt
from datetime import datetime
import pytz # Recommended for timezone handling if needed (NEEDS INSTALL: pip install pytz)

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
        # Ensure _id exists before accessing
        return str(self.data.get('_id')) if self.data.get('_id') else None


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
         # Example: Convert to a specific timezone using pytz if needed upon retrieval
         # if dt and pytz:
         #     utc_dt = pytz.utc.localize(dt) # Assume stored as naive UTC
         #     target_tz = pytz.timezone('America/New_York') # Example TZ
         #     return utc_dt.astimezone(target_tz)
         return dt # Return as stored for now

    @property
    def is_admin(self):
        return self.role == 'admin'

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        pw_hash = self.password_hash
        if not pw_hash:
            return False
        # Ensure password is bytes if hash is bytes, or both strings
        try:
            return bcrypt.check_password_hash(pw_hash, password)
        except ValueError as e:
            print(f"Error checking password for user {self.username}: {e}")
            # Handle potential hash/password format mismatch issues
            return False


    # --- Static methods for DB operations ---
    @staticmethod
    def get_collection():
        """Helper to get the users collection."""
        # Added check for mongo object initialization
        if not mongo or not hasattr(mongo, 'db'):
             print("ERROR: mongo object not initialized before accessing collection.")
             # Handle this case appropriately, maybe raise an exception or return None
             # Depending on where it's called, this might indicate a larger startup issue.
             return None
        return mongo.db.users

    @staticmethod
    def find_by_username(username):
        """Finds a user document by username."""
        collection = User.get_collection()
        return collection.find_one({'username': username}) if collection else None


    @staticmethod
    def find_by_email(email):
        """Finds a user document by email."""
        collection = User.get_collection()
        # Case-insensitive email search often useful
        return collection.find_one({'email': {'$regex': f'^{email}$', '$options': 'i'}}) if collection else None


    @staticmethod
    def get_by_id(user_id):
        """Finds a user by MongoDB ObjectId string and returns a User object."""
        collection = User.get_collection()
        if not collection: return None
        try:
            user_data = collection.find_one({'_id': ObjectId(user_id)})
            if user_data:
                return User(user_data) # Return the wrapper object
        except Exception as e: # Handle invalid ObjectId format or other errors
            print(f"Error finding user by ID {user_id}: {e}")
            return None
        return None

    @staticmethod
    def create(username, email, password, role='user'):
        """Creates a new user in the database. Returns User object or None."""
        collection = User.get_collection()
        if not collection:
             print(f"Cannot create user {username}: User collection not available.")
             return None

        # Basic validation before DB check
        if not username or not email or not password:
             print(f"Cannot create user: Missing username, email, or password.")
             return None

        # Use case-insensitive check
        existing_user_by_name = collection.find_one({'username': {'$regex': f'^{username}$', '$options': 'i'}})
        existing_user_by_email = collection.find_one({'email': {'$regex': f'^{email}$', '$options': 'i'}})

        if existing_user_by_name:
            print(f"Attempt to create existing user (username match): {username}")
            return None # User already exists
        if existing_user_by_email:
             print(f"Attempt to create existing user (email match): {email}")
             return None # Email already exists


        try:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user_doc = {
                'username': username, # Store original case? Or normalize? Let's keep original for display.
                'email': email.lower(), # Store email in lowercase for consistency
                'password_hash': hashed_password,
                'role': role,
                'created_at': datetime.utcnow() # Store in UTC
            }
            result = collection.insert_one(user_doc)
            print(f"User created with ID: {result.inserted_id}")
            return User.get_by_id(result.inserted_id)
        except Exception as e:
            print(f"Error creating user {username}: {e}")
            # Log the error properly in a real application
            return None


    @staticmethod
    def get_all_users():
        """Retrieves all user documents."""
        collection = User.get_collection()
        if not collection: return []
        return list(collection.find().sort('username', 1))


    @staticmethod
    def update_role(user_id, new_role):
        """Updates the role for a given user ID."""
        collection = User.get_collection()
        if not collection: return False

        if new_role not in ['user', 'admin']:
            print(f"Invalid role specified for update: {new_role}")
            return False # Invalid role
        try:
            result = collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'role': new_role}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating role for user {user_id}: {e}")
            return False

# --- Project/Task DB Helpers ---

def get_projects_collection():
    if not mongo or not hasattr(mongo, 'db'):
        print("ERROR: mongo object not initialized before accessing project collection.")
        return None
    return mongo.db.projects

# We are embedding tasks, so no separate tasks collection needed for this example

def create_project(name, description, owner_id, status="Not Started", due_date=None):
    """Creates a new project document."""
    collection = get_projects_collection()
    if not collection:
         print(f"Cannot create project {name}: Project collection not available.")
         return None

    if not name or not owner_id:
        print("Cannot create project: Missing name or owner_id.")
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
        result = collection.insert_one(project_doc)
        return result.inserted_id
    except Exception as e:
        print(f"Error creating project {name}: {e}")
        return None


def get_project_by_id(project_id):
    """Retrieves a project document by its ID."""
    collection = get_projects_collection()
    if not collection: return None
    try:
        return collection.find_one({'_id': ObjectId(project_id)})
    except Exception as e:
        print(f"Error fetching project by ID {project_id}: {e}")
        return None


def get_projects_for_user(user_id):
    """Finds projects owned by the user. Expand later for assigned projects."""
    collection = get_projects_collection()
    if not collection: return []
    try:
        # Simple query for owned projects, sorted by most recently created
        return list(collection.find(
            {'owner_id': ObjectId(user_id)}
        ).sort('created_at', -1))
    except Exception as e:
        print(f"Error fetching projects for user {user_id}: {e}")
        return []


def add_task_to_project(project_id, name, description, created_by_id, status="To Do", due_date=None, assigned_to_id=None):
    """Adds a task sub-document to a project."""
    collection = get_projects_collection()
    if not collection:
         print(f"Cannot add task to project {project_id}: Project collection not available.")
         return None

    if not name or not project_id or not created_by_id:
        print("Cannot add task: Missing name, project_id, or created_by_id.")
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
        result = collection.update_one(
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
    collection = get_projects_collection()
    if not collection: return None
    try:
        project = collection.find_one(
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
    collection = get_projects_collection()
    if not collection: return False
    try:
        result = collection.update_one(
            # Ensure task_id is ObjectId for matching
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
    collection = get_projects_collection()
    if not collection: return False
    try:
        result = collection.delete_one({'_id': ObjectId(project_id)})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting project {project_id}: {e}")
        return False

# Example: Delete Task (pull from embedded array)
def delete_task_from_project(project_id, task_id):
     collection = get_projects_collection()
     if not collection: return False
     try:
         result = collection.update_one(
             {'_id': ObjectId(project_id)},
             # Ensure task_id is ObjectId for matching in pull
             {'$pull': {'tasks': {'_id': ObjectId(task_id)}},
              '$set': {'last_updated': datetime.utcnow()}
             }
         )
         return result.modified_count > 0
     except Exception as e:
         print(f"Error deleting task {task_id} from project {project_id}: {e}")
         return False