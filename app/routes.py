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

@bp.route('/crawler')
@login_required
def crawler():
    return render_template('crawler/index.html')

@bp.route('/api/crawl')
@login_required
def api_crawl():
    keyword = request.args.get('keyword')
    if not keyword:
        return jsonify({'error': 'Keyword is required'}), 400
    
    try:
        data = crawl_baidu_news(keyword)
        return jsonify({'data': data, 'count': len(data)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
