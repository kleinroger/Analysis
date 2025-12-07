from flask import Blueprint

bp = Blueprint('ai_engine', __name__)

from . import routes
