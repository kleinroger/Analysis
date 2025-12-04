from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from .auth import login_required
from .crawler import crawl_baidu_news

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@bp.route('/reports')
@login_required
def reports():
    from .db import get_db
    db = get_db()
    latest = db.execute('SELECT title, body, created_at FROM reports ORDER BY id DESC LIMIT 1').fetchone()
    return render_template('reports/index.html', latest=latest)
