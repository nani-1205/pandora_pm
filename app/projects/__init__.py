# pandora_pm/app/projects/__init__.py
from flask import Blueprint
bp = Blueprint('projects', __name__)
from . import routes