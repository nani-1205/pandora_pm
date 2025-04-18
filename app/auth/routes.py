from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from email_validator import validate_email, EmailNotValidError # For basic validation
from . import bp
from ..models import User # Import the User wrapper class

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        password2 = request.form.get('password2')

        # --- Basic Server-Side Validation ---
        error = None
        if not username: error = 'Username is required.'
        elif not email: error = 'Email is required.'
        elif not password: error = 'Password is required.'
        elif password != password2: error = 'Passwords do not match.'
        else:
             try:
                 # Validate email format
                 valid = validate_email(email)
                 email = valid.email # Normalized email
             except EmailNotValidError as e:
                  error = str(e)

        if error:
             flash(error, 'danger')
        else:
            # Check if username or email already exists
            if User.find_by_username(username):
                flash(f'Username "{username}" is already taken. Please choose another.', 'warning')
            elif User.find_by_email(email):
                flash(f'Email "{email}" is already registered.', 'warning')
            else:
                # Attempt to create user
                # Determine role (e.g., first user is admin)
                is_first_user = User.get_collection().count_documents({}) == 0
                role = 'admin' if is_first_user else 'user'

                new_user = User.create(username, email, password, role=role)
                if new_user:
                    flash(f'Registration successful for {username}! Welcome to Pandora PM. Please log in.', 'success')
                    if is_first_user:
                        flash('You have been registered as the first user (Admin).', 'info')
                    return redirect(url_for('auth.login'))
                else:
                    # Generic error if create fails (error logged in User.create)
                    flash('An unexpected error occurred during registration. Please try again.', 'danger')

    return render_template('auth/register.html', title='Register')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if not username or not password:
            flash('Both username and password are required.', 'danger')
            return redirect(url_for('auth.login'))

        user_data = User.find_by_username(username) # Find the dict first
        user = User(user_data) if user_data else None # Create User object wrapper if found

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Login successful! Welcome back, {user.username}!', 'success')

            # Redirect to the page user was trying to access, or dashboard
            next_page = request.args.get('next')
            # Security: Ensure next_page is relative within the site
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('main.dashboard')
            return redirect(next_page)
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('auth/login.html', title='Login')

@bp.route('/logout')
@login_required # User must be logged in to log out
def logout():
    logout_user()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('auth.login'))