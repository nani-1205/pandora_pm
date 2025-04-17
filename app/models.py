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
        # Ensure ID is always returned as string
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

    # === Add Debugging to User.get_by_id ===
    @staticmethod
    def get_by_id(user_id):
        # --- DEBUG ---
        print(f"--- User.get_by_id: Attempting to find user with raw id: '{user_id}' (type: {type(user_id)}) ---")
        # --- END DEBUG ---
        try:
            user_obj_id = ObjectId(user_id)
             # --- DEBUG ---
            print(f"--- User.get_by_id: Converted id to ObjectId: {user_obj_id} ---")
             # --- END DEBUG ---
            user_data = mongo.db.users.find_one({'_id': user_obj_id})
            # --- DEBUG ---
            print(f"--- User.get_by_id: Found user data: {'Yes' if user_data else 'No'} ---")
            # --- END DEBUG ---
            if user_data:
                return User(user_data)
        except (bson_errors.InvalidId, TypeError) as e:
            # --- DEBUG ---
            print(f"--- User.get_by_id: ERROR converting id '{user_id}' to ObjectId: {e} ---")
            # --- END DEBUG ---
            return None
        except Exception as e:
             # --- DEBUG ---
            print(f"--- User.get_by_id: UNEXPECTED ERROR finding user '{user_id}': {e} ---")
             # --- END DEBUG ---
            return None
        return None
    # === End Debugging in User.get_by_id ===

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
            # Return the User object wrapper for the newly created user
            return User.get_by_id(result.inserted_id)
        except Exception as e:
            print(f"Error creating user: {e}") # Log this properly
            return None

    @staticmethod
    def get_all_users():
        # Return sorted list of user dicts
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
            'owner_id': ObjectId(owner_id), # Ensure owner_id is stored as ObjectId
            'status': status,
            'due_date': due_date,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'tasks': []
        }
        result = mongo.db.projects.insert_one(project_doc)
        return str(result.inserted_id)
    except (bson_errors.InvalidId, TypeError):
         print(f"Error creating project: Invalid owner_id format '{owner_id}'.")
         return None
    except Exception as e:
        print(f"Error creating project: {e}")
        return None

def get_project_by_id(project_id):
    try:
        return mongo.db.projects.find_one({'_id': ObjectId(project_id)})
    except (bson_errors.InvalidId, TypeError):
        return None

# === VERIFIED/CORRECTED FUNCTION with extra debugging ===
def get_projects_for_user(user_id):
    """
    Finds projects where the user is the owner OR is assigned to any task within the project.
    Uses aggregation for efficiency.
    """
    print(f"\n--- models.py/get_projects_for_user: Called with user_id: '{user_id}' (type: {type(user_id)}) ---") # Print input type

    try:
        # --- CRITICAL: Ensure user_id is converted to ObjectId for comparison ---
        user_obj_id = ObjectId(user_id)
        print(f"--- models.py/get_projects_for_user: Converted input to user ObjectId: {user_obj_id} ---")

        pipeline = [
            {
                '$match': {
                    '$or': [
                        # Compare owner_id (stored as ObjectId) with the user's ObjectId
                        {'owner_id': user_obj_id},
                        # Compare assigned_to (stored as ObjectId) in tasks array with user's ObjectId
                        {'tasks.assigned_to': user_obj_id}
                    ]
                }
            },
            # Add a project stage to see exactly what's being matched BEFORE sorting
            # This helps confirm the $match is working as expected
            {'$project': {'name': 1, 'owner_id': 1, 'tasks.assigned_to': 1, 'created_at': 1, 'status': 1, 'description': 1, 'due_date': 1, 'tasks': 1, 'updated_at': 1}}, # Project all needed fields
            {
                '$sort': {'created_at': -1} # Sort the results (optional)
            }
        ]
        print(f"--- models.py/get_projects_for_user: Executing Aggregation Pipeline for {user_obj_id} ---")
        # print(f"--- Pipeline: {pipeline} ---") # Uncomment if needed, can be verbose

        projects = list(mongo.db.projects.aggregate(pipeline))

        print(f"--- models.py/get_projects_for_user: Found {len(projects)} projects for user ObjectId: {user_obj_id} via AGGREGATION ---")
        if projects:
             print(f"--- models.py/get_projects_for_user: Aggregation Project[0] (example): {projects[0]} ---")


        # --- TEMPORARY: Also run simple find for direct comparison ---
        print(f"--- models.py/get_projects_for_user: Running simple find({'owner_id': user_obj_id}) for comparison ---")
        simple_find_results = list(mongo.db.projects.find({'owner_id': user_obj_id}))
        print(f"--- models.py/get_projects_for_user: Simple find() found {len(simple_find_results)} projects ---")
        if simple_find_results:
            print(f"--- models.py/get_projects_for_user: Simple find() Project[0] owner_id: {simple_find_results[0].get('owner_id')} ---")
            # Return the full document from find if aggregation seems problematic during debug
            # return simple_find_results # <--- TEMPORARY DEBUG STEP
        # --- END TEMPORARY ---


        # Return the results from the aggregation pipeline (normal operation)
        return projects

    except (bson_errors.InvalidId, TypeError):
        # This error occurs if the user_id string passed in cannot be converted to ObjectId
        print(f"--- models.py/get_projects_for_user: ERROR converting user_id '{user_id}' to ObjectId. ---")
        return []
    except Exception as e:
        print(f"--- models.py/get_projects_for_user: ERROR during aggregation for user {user_id}: {e} ---")
        return []
# === END VERIFIED/CORRECTED FUNCTION ===


def add_task_to_project(project_id, name, description, created_by_id, status="To Do", due_date=None, assigned_to_id=None):
     try:
        # Ensure assigned_to_id is converted to ObjectId if present
        assignee_obj_id = ObjectId(assigned_to_id) if assigned_to_id else None

        task_doc = {
            '_id': ObjectId(),
            'project_id_ref': ObjectId(project_id),
            'name': name,
            'description': description,
            'status': status,
            'due_date': due_date,
            'created_by': ObjectId(created_by_id),
            'assigned_to': assignee_obj_id, # Use the converted ObjectId or None
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        result = mongo.db.projects.update_one(
            {'_id': ObjectId(project_id)},
            {'$push': {'tasks': task_doc}}
        )
        if result.modified_count > 0:
            return str(task_doc['_id'])
        else:
            return None
     except (bson_errors.InvalidId, TypeError):
        print(f"Error adding task: Invalid ObjectId format for project '{project_id}', creator '{created_by_id}', or assignee '{assigned_to_id}'.")
        return None
     except Exception as e:
        print(f"Error adding task: {e}")
        return None

def get_task_from_project(project_id, task_id):
    try:
        project = mongo.db.projects.find_one(
            {'_id': ObjectId(project_id), 'tasks._id': ObjectId(task_id)},
            {'tasks.$': 1}
        )
        if project and 'tasks' in project and len(project['tasks']) == 1:
            return project['tasks'][0]
        return None
    except (bson_errors.InvalidId, TypeError):
        return None

def update_task_status_in_project(project_id, task_id, new_status):
    try:
        result = mongo.db.projects.update_one(
            {'_id': ObjectId(project_id), 'tasks._id': ObjectId(task_id)},
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
             {'$pull': {'tasks': {'_id': ObjectId(task_id)}}}
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
    users = User.get_all_users()
    if users:
        return {str(user['_id']): user.get('username', 'Unknown') for user in users}
    return {}

# --- Update Task Function ---
def update_task_in_project(project_id, task_id, update_data):
    set_update = {f'tasks.$.{key}': value for key, value in update_data.items()}
    set_update['tasks.$.updated_at'] = datetime.utcnow()
    if 'assigned_to' in set_update:
        assignee_val = set_update['tasks.$.assigned_to']
        if assignee_val:
             try: set_update['tasks.$.assigned_to'] = ObjectId(assignee_val)
             except (bson_errors.InvalidId, TypeError):
                 print(f"Error updating task: Invalid assigned_to ID format '{assignee_val}'.")
                 return False
        else: set_update['tasks.$.assigned_to'] = None
    try:
        result = mongo.db.projects.update_one(
            {'_id': ObjectId(project_id), 'tasks._id': ObjectId(task_id)},
            {'$set': set_update} )
        # Return True if matched, even if no fields changed (update operation itself succeeded)
        return result.matched_count > 0
    except (bson_errors.InvalidId, TypeError):
        print("Error updating task: Invalid project or task ID format.")
        return False
    except Exception as e:
        print(f"Error updating task details: {e}")
        return False