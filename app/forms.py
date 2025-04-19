# app/forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField, TextAreaField,
    SelectField, DateField, DateTimeLocalField # Added DateTimeLocalField
)
from wtforms.validators import (
    DataRequired, Length, Email, EqualTo, ValidationError, Optional
)
from .models import User, Project, TASK_STATUS_CHOICES, THEME_CHOICES, AVAILABLE_THEMES, WorkPackage
from datetime import datetime

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        if User.objects(username=username.data).first(): raise ValidationError('Username taken.')
    def validate_email(self, email):
        if User.objects(email=email.data).first(): raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(max=120)])
    description = TextAreaField('Description')
    submit = SubmitField('Create Project')

class WorkPackageForm(FlaskForm):
    name = StringField('Work Package Name', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Description')
    start_date = DateField('Start Date (Optional)', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('End Date (Optional)', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Create Work Package')

    def validate_end_date(self, end_date):
        if end_date.data and self.start_date.data and end_date.data < self.start_date.data:
            raise ValidationError('End date must not be earlier than start date.')

class MilestoneForm(FlaskForm):
    name = StringField('Milestone Name', validators=[DataRequired(), Length(max=150)])
    target_date = DateField('Target Date', format='%Y-%m-%d', validators=[DataRequired()])
    description = TextAreaField('Description (Optional)')
    submit = SubmitField('Create Milestone')

class TaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    work_package = SelectField('Work Package (Optional)', coerce=str, validators=[Optional()])
    assigned_to = SelectField('Assign To', coerce=str, validators=[DataRequired()])
    status = SelectField('Status', choices=TASK_STATUS_CHOICES, default='To Do', validators=[DataRequired()])
    due_date = DateField('Due Date (Optional)', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Create Task')

    def __init__(self, project_id=None, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.assigned_to.choices = [(str(user.id), user.username) for user in User.objects.order_by('username')]
        if project_id:
            wp_choices = [('', '--- None ---')]
            wps = WorkPackage.objects(project=project_id).order_by('name')
            wp_choices.extend([(str(wp.id), wp.name) for wp in wps])
            self.work_package.choices = wp_choices
        else: self.work_package.choices = [('', '--- Select Project First ---')]

class UpdateTaskStatusForm(FlaskForm):
    status = SelectField('Status', choices=TASK_STATUS_CHOICES, validators=[DataRequired()])
    submit = SubmitField('Update Status')

class UpdateProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    theme = SelectField('Theme', choices=THEME_CHOICES, validators=[DataRequired()])
    submit = SubmitField('Update Profile')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(UpdateProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username; self.original_email = original_email
    def validate_username(self, username):
        if username.data != self.original_username and User.objects(username=username.data).first(): raise ValidationError('Username taken.')
    def validate_email(self, email):
        if email.data != self.original_email and User.objects(email=email.data).first(): raise ValidationError('Email registered.')
    def validate_theme(self, theme):
        if theme.data not in AVAILABLE_THEMES: raise ValidationError('Invalid theme.')

class CalendarEventForm(FlaskForm):
    title = StringField('Event Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    start_time = DateTimeLocalField('Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_time = DateTimeLocalField('End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    all_day = BooleanField('All Day Event')
    submit = SubmitField('Save Event')

    def validate_end_time(self, end_time):
        if end_time.data and self.start_time.data and end_time.data <= self.start_time.data:
            if not (self.all_day.data and end_time.data.date() >= self.start_time.data.date()):
                 raise ValidationError('End time must be after start time.')

# --- ChatGroup Form (NEW) ---
class ChatGroupForm(FlaskForm):
    name = StringField('Group Name', validators=[DataRequired(), Length(min=3, max=100)])
    submit = SubmitField('Create Group')

# --- ChatMessage Form (NEW) ---
class ChatMessageForm(FlaskForm):
    content = TextAreaField('Message', validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField('Send') # Button might be handled by JS