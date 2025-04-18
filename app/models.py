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
    def id(self): return str(self.data.get('_id'))
    @property
    def username(self): return self.data.get('username')
    @property
    def email(self): return self.data.get('email')
    @property
    def role(self): return self.data.get('role', 'user')
    @property
    def is_admin(self): return self.role == 'admin'

    def check_password(self, password):
        stored_hash = self.data.get('password_hash')
        if stored_hash: return bcrypt.check_password_hash(stored_hash, password)
        return False

    @staticmethod
    def find_by_username(username): return mongo.db.users.find_one({'username': username})
    @staticmethod
    def find_by_email(email): return mongo.db.users.find_one({'email': email})

    @staticmethod
    def get_by_id(user_id):
        # print(f"--- User.get_by_id: Attempting id: '{user_id}' ---") # Debug
        try:
            user_obj_id = ObjectId(user_id)
            user_data = mongo.db.users.find_one({'_id': user_obj_id})
            # print(f"--- User.get_by_id: Found data: {'Yes' if user_data else 'No'} ---") # Debug
            if user_data: return User(user_data)
        except (bson_errors.InvalidId, TypeError) as e: print(f"--- User.get_by_id: ERROR converting id '{user_id}': {e} ---"); return None
        except Exception as e: print(f"--- User.get_by_id: UNEXPECTED ERROR finding user '{user_id}': {e} ---"); return None
        return None

    @staticmethod
    def create(username, email, password, role='user'):
        if User.find_by_username(username) or User.find_by_email(email): return None
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user_doc = {'username': username,'email': email,'password_hash': hashed_password,'role': role,'created_at': datetime.utcnow()}
        try:
            result = mongo.db.users.insert_one(user_doc)
            return User.get_by_id(result.inserted_id)
        except Exception as e: print(f"Error creating user: {e}"); return None

    @staticmethod
    def get_all_users(): return list(mongo.db.users.find().sort('username', 1))

    @staticmethod
    def set_role(user_id, role):
         if role not in ['admin', 'user']: return False
         try:
             result = mongo.db.users.update_one({'_id': ObjectId(user_id)},{'$set': {'role': role}})
             return result.modified_count > 0
         except (bson_errors.InvalidId, TypeError): return False
         except Exception as e: print(f"Error setting user role: {e}"); return False

# --- Project/Task Helpers ---

def create_project(name, description, owner_id, status="Not Started", due_date=None):
    try:
        project_doc = {'name': name,'description': description,'owner_id': ObjectId(owner_id),'status': status,'due_date': due_date,'created_at': datetime.utcnow(),'updated_at': datetime.utcnow(),'tasks': []}
        result = mongo.db.projects.insert_one(project_doc)
        return str(result.inserted_id)
    except (bson_errors.InvalidId, TypeError): print(f"Error creating project: Invalid owner_id format '{owner_id}'."); return None
    except Exception as e: print(f"Error creating project: {e}"); return None

def get_project_by_id(project_id):
    try: return mongo.db.projects.find_one({'_id': ObjectId(project_id)})
    except (bson_errors.InvalidId, TypeError): return None

# === CORRECTED FUNCTION (Removed $project stage) ===
def get_projects_for_user(user_id):
    """ Finds projects user owns OR is assigned to tasks in. """
    # print(f"\n--- models.py/get_projects_for_user: Called with user_id: '{user_id}' ---") # Debug
    try:
        user_obj_id = ObjectId(user_id)
        # print(f"--- models.py/get_projects_for_user: Converted to ObjectId: {user_obj_id} ---") # Debug
        pipeline = [
            {'$match': {'$or': [{'owner_id': user_obj_id},{'tasks.assigned_to': user_obj_id}]}},
            # REMOVED $project stage - was causing path collision error
            {'$sort': {'created_at': -1}}
        ]
        # print(f"--- models.py/get_projects_for_user: Executing Aggregation for {user_obj_id} ---") # Debug
        projects = list(mongo.db.projects.aggregate(pipeline))
        # print(f"--- models.py/get_projects_for_user: Found {len(projects)} projects ---") # Debug
        return projects
    except (bson_errors.InvalidId, TypeError): print(f"--- models.py/get_projects_for_user: ERROR converting user_id '{user_id}' to ObjectId. ---"); return []
    except Exception as e: print(f"--- models.py/get_projects_for_user: ERROR during aggregation for user {user_id}: {e} ---"); return []

def add_task_to_project(project_id, name, description, created_by_id, status="To Do", due_date=None, assigned_to_id=None):
     # print(f"\n--- models.add_task_to_project: ENTERING: assigned_to='{assigned_to_id}' ---") # Debug
     try:
        assignee_obj_id = ObjectId(assigned_to_id) if assigned_to_id else None
        project_obj_id = ObjectId(project_id)
        creator_obj_id = ObjectId(created_by_id)
        task_doc = {
            '_id': ObjectId(), 'project_id_ref': project_obj_id, 'name': name, 'description': description,
            'status': status, 'due_date': due_date, 'created_by': creator_obj_id,
            'assigned_to': assignee_obj_id, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()
        }
        # print(f"--- models.add_task_to_project: Task doc: {task_doc} ---") # Debug
        update_result = mongo.db.projects.update_one({'_id': project_obj_id}, {'$push': {'tasks': task_doc}})
        # print(f"--- models.add_task_to_project: Update Result: matched={update_result.matched_count}, modified={update_result.modified_count} ---") # Debug
        if update_result.modified_count > 0: return str(task_doc['_id'])
        else: print(f"--- models.add_task_to_project: FAILED - Project not found or modified_count=0 ---"); return None
     except (bson_errors.InvalidId, TypeError) as id_error: print(f"--- models.add_task_to_project: ERROR - Invalid ObjectId format: {id_error} ---"); return None
     except Exception as e: print(f"--- models.add_task_to_project: UNEXPECTED ERROR: {e} ---"); return None

def get_task_from_project(project_id, task_id):
    try:
        project = mongo.db.projects.find_one( {'_id': ObjectId(project_id), 'tasks._id': ObjectId(task_id)}, {'tasks.$': 1} )
        if project and 'tasks' in project and len(project['tasks']) == 1: return project['tasks'][0]
    except (bson_errors.InvalidId, TypeError): pass
    return None

def update_task_status_in_project(project_id, task_id, new_status):
    try:
        result = mongo.db.projects.update_one( {'_id': ObjectId(project_id), 'tasks._id': ObjectId(task_id)}, {'$set': {'tasks.$.status': new_status, 'tasks.$.updated_at': datetime.utcnow()}} )
        return result.modified_count > 0
    except (bson_errors.InvalidId, TypeError): return False
    except Exception as e: print(f"Error updating task status: {e}"); return False

def delete_task_from_project(project_id, task_id):
     try:
         result = mongo.db.projects.update_one( {'_id': ObjectId(project_id)}, {'$pull': {'tasks': {'_id': ObjectId(task_id)}}} )
         return result.modified_count > 0
     except (bson_errors.InvalidId, TypeError): return False
     except Exception as e: print(f"Error deleting task: {e}"); return False

def delete_project(project_id):
    try:
        result = mongo.db.projects.delete_one({'_id': ObjectId(project_id)})
        return result.deleted_count > 0
    except (bson_errors.InvalidId, TypeError): return False
    except Exception as e: print(f"Error deleting project: {e}"); return False

def get_user_dict():
    users = User.get_all_users()
    if users: return {str(user['_id']): user.get('username', 'Unknown') for user in users}
    return {}

def update_task_in_project(project_id, task_id, update_data):
    set_update = {f'tasks.$.{key}': value for key, value in update_data.items()}
    set_update['tasks.$.updated_at'] = datetime.utcnow()
    if 'assigned_to' in set_update:
        assignee_val = set_update['tasks.$.assigned_to']
        if assignee_val:
             try: set_update['tasks.$.assigned_to'] = ObjectId(assignee_val)
             except (bson_errors.InvalidId, TypeError): print(f"Error updating task: Invalid assigned_to ID format '{assignee_val}'."); return False
        else: set_update['tasks.$.assigned_to'] = None
    try:
        result = mongo.db.projects.update_one( {'_id': ObjectId(project_id), 'tasks._id': ObjectId(task_id)}, {'$set': set_update} )
        return result.matched_count > 0
    except (bson_errors.InvalidId, TypeError): print("Error updating task: Invalid project or task ID format."); return False
    except Exception as e: print(f"Error updating task details: {e}"); return False