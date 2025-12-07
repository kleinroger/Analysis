from flask import Blueprint

bp = Blueprint('crawler_mgmt', __name__, template_folder='../templates')

from . import routes
