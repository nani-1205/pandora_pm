# pandora_pm/app/auth/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from . import bp
from ..models import User
# === NEW: Import mongo extension for database access ===
from ..extensions import mongo
# === END NEW ===
# from ..forms import LoginForm, RegistrationForm # Uncomment if using Flask-WTF

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Basic HTML Form handling:
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2') # Basic confirmation

        error = None
        if not username: error = 'Username is required.'
        elif not email: error = 'Email is required.'
        elif '@' not in email or '.' not in email: error = 'Invalid email format.' # Basic check
        elif not password: error = 'Password is required.'
        elif password != password2: error = 'Passwords do not match.'
        # Add more validation (e.g., password complexity) here if needed

        if error:
            flash(error, 'danger')
        else:
            # Check if user already exists *before* counting for first user check
            existing_user = User.find_by_username(username) or User.find_by_email(email)
            if existing_user:
                flash('Username or email already exists.', 'warning')
            else:
                # --- Determine Role based on user count ---
                try:
                    # Count existing documents in the users collection
                    user_count = mongo.db.users.count_documents({})
                    # Assign 'admin' role if this is the very first user (count is 0)
                    role_to_assign = 'admin' if user_count == 0 else 'user'
                    print(f"User count: {user_count}, Assigning role: {role_to_assign}") # Debugging output
                except Exception as e:
                    # Handle potential DB connection errors during count
                    flash('Database error checking user count. Cannot register.', 'danger')
                    print(f"Error counting users: {e}") # Log the error
                    # Optional: redirect back to registration or show an error page
                    return render_template('auth/register.html', title='Register')
                # --- End Role Determination ---

                # Create user with the determined role
                user = User.create(username, email, password, role=role_to_assign)
                if user:
                    flash(f'Registration successful! {"You have been assigned the Admin role." if role_to_assign == "admin" else ""} Please log in.', 'success')
                    return redirect(url_for('auth.login'))
                else:
                    # This could happen if User.create fails for some reason (e.g., race condition on username check)
                    flash('An error occurred during registration after role check.', 'danger')

    return render_template('auth/register.html', title='Register')


# --- LOGIN Route (remains the same) ---
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Basic HTML Form handling:
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        error = None
        if not username: error = 'Username is required.'
        elif not password: error = 'Password is required.'

        if error:
            flash(error, 'danger')
        else:
            user_data = User.find_by_username(username)
            user_obj = User(user_data) if user_data else None # Create wrapper object

            if user_obj and user_obj.check_password(password):
                login_user(user_obj, remember=remember)
                flash('Login successful!', 'success')
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('main.dashboard')
                return redirect(next_page)
            else:
                flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html', title='Login')

# --- LOGOUT Route (remains the same) ---
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))