from flask import Blueprint

bp = Blueprint('rules', __name__)

from . import routes