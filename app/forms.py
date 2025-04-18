# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
# --- Import theme choices and User model ---
from .models import User, Project, TASK_STATUS_CHOICES, THEME_CHOICES, AVAILABLE_THEMES # Import User and Theme constants

class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email',
                        validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    # Custom validators
    def validate_username(self, username):
        user = User.objects(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.objects(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please use a different one or log in.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(max=120)])
    description = TextAreaField('Description')
    submit = SubmitField('Create Project')

class TaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    assigned_to = SelectField('Assign To', coerce=str, validators=[DataRequired()]) # Use user ID as string
    status = SelectField('Status', choices=TASK_STATUS_CHOICES, default='To Do', validators=[DataRequired()])
    due_date = DateField('Due Date (Optional)', format='%Y-%m-%d', validators=None) # Optional field
    submit = SubmitField('Create Task')

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        # Populate the 'assigned_to' choices dynamically with existing users
        self.assigned_to.choices = [(str(user.id), user.username) for user in User.objects.order_by('username')]

class UpdateTaskStatusForm(FlaskForm):
    status = SelectField('Status', choices=TASK_STATUS_CHOICES, validators=[DataRequired()])
    submit = SubmitField('Update Status')


# --- NEW PROFILE FORM ---
class UpdateProfileForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email',
                        validators=[DataRequired(), Email(), Length(max=100)])
    theme = SelectField('Theme', choices=THEME_CHOICES, validators=[DataRequired()])
    submit = SubmitField('Update Profile')

    # Need to know the original user to validate changes
    def __init__(self, original_username, original_email, *args, **kwargs):
        super(UpdateProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    # Custom validators to check if username/email changed AND is already taken
    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.objects(username=username.data).first()
            if user:
                raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email):
         if email.data != self.original_email:
            user = User.objects(email=email.data).first()
            if user:
                raise ValidationError('That email is already registered. Please use a different one.')

    # Validate selected theme is one of the available ones
    def validate_theme(self, theme):
        if theme.data not in AVAILABLE_THEMES:
            raise ValidationError('Invalid theme selected.')