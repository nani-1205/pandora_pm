# pandora_pm/app/auth/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from . import bp
from ..models import User
# from ..forms import LoginForm, RegistrationForm # Uncomment if using Flask-WTF

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # If using Flask-WTF:
    # form = RegistrationForm()
    # if form.validate_on_submit():
    #     user = User.create(username=form.username.data, email=form.email.data, password=form.password.data)
    #     if user:
    #         flash('Congratulations, you are now a registered user!', 'success')
    #         return redirect(url_for('auth.login'))
    #     else:
    #         flash('Registration failed. Username or email might already exist.', 'danger')
    # return render_template('auth/register.html', title='Register', form=form)

    # Basic HTML Form handling:
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2') # Basic confirmation

        error = None
        if not username: error = 'Username is required.'
        elif not email: error = 'Email is required.'
        elif not password: error = 'Password is required.'
        elif password != password2: error = 'Passwords do not match.'
        # Add more validation (email format, password complexity) here

        if error:
            flash(error, 'danger')
        else:
            # Check if user exists
            existing_user = User.find_by_username(username) or User.find_by_email(email)
            if existing_user:
                flash('Username or email already exists.', 'warning')
            else:
                # Create user (Maybe make the very first user an admin?)
                # is_first_user = mongo.db.users.count_documents({}) == 0
                # role = 'admin' if is_first_user else 'user'
                user = User.create(username, email, password) # Default role is 'user'
                if user:
                    flash('Registration successful! Please log in.', 'success')
                    return redirect(url_for('auth.login'))
                else:
                    flash('An error occurred during registration.', 'danger')

    return render_template('auth/register.html', title='Register')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # If using Flask-WTF:
    # form = LoginForm()
    # if form.validate_on_submit():
    #     user_data = User.find_by_username(form.username.data)
    #     user = User(user_data) if user_data else None
    #     if user is None or not user.check_password(form.password.data):
    #         flash('Invalid username or password', 'danger')
    #         return redirect(url_for('auth.login'))
    #     login_user(user, remember=form.remember_me.data)
    #     next_page = request.args.get('next')
    #     if not next_page or url_parse(next_page).netloc != '': # Security check
    #         next_page = url_for('main.dashboard')
    #     return redirect(next_page)
    # return render_template('auth/login.html', title='Sign In', form=form)

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
                 # Security: Ensure next_page is internal
                if not next_page or url_parse(next_page).netloc != '':
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