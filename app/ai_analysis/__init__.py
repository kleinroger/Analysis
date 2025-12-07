from flask import Blueprint

bp = Blueprint('ai_analysis', __name__, template_folder='../templates')

from . import routes
