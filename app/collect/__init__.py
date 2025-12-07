from flask import Blueprint

bp = Blueprint('collect', __name__)

from . import routes
