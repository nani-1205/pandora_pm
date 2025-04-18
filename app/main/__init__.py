from flask import Blueprint
bp = Blueprint('main', __name__)
from . import routes # Import routes after blueprint creation