# pandora_pm/app/auth/__init__.py
from flask import Blueprint
bp = Blueprint('auth', __name__)
from . import routes