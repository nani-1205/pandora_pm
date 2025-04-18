# pandora_pm/app/auth/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from . import bp
from ..models import User
from ..extensions import mongo # Needed for user count

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2')

        error = None
        if not username: error = 'Username is required.'
        elif not email: error = 'Email is required.'
        elif '@' not in email or '.' not in email: error = 'Invalid email format.'
        elif not password: error = 'Password is required.'
        elif password != password2: error = 'Passwords do not match.'

        if error:
            flash(error, 'danger')
        else:
            existing_user = User.find_by_username(username) or User.find_by_email(email)
            if existing_user:
                flash('Username or email already exists.', 'warning')
            else:
                try:
                    user_count = mongo.db.users.count_documents({})
                    role_to_assign = 'admin' if user_count == 0 else 'user'
                    # print(f"User count: {user_count}, Assigning role: {role_to_assign}") # Debug
                except Exception as e:
                    flash('Database error checking user count. Cannot register.', 'danger')
                    print(f"Error counting users: {e}")
                    return render_template('auth/register.html', title='Register')

                user = User.create(username, email, password, role=role_to_assign)
                if user:
                    flash(f'Registration successful! {"You have been assigned the Admin role." if role_to_assign == "admin" else ""} Please log in.', 'success')
                    return redirect(url_for('auth.login'))
                else:
                    flash('An error occurred during registration after role check.', 'danger')

    return render_template('auth/register.html', title='Register')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

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
            user_obj = User(user_data) if user_data else None

            if user_obj and user_obj.check_password(password):
                login_user(user_obj, remember=remember)
                # flash('Login successful!', 'success') # Can be noisy
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('main.dashboard')
                return redirect(next_page)
            else:
                flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html', title='Login')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))