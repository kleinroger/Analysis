from flask import Blueprint, render_template, request, redirect, url_for
from .auth import login_required, role_required
from .db import get_db
from werkzeug.security import generate_password_hash

bp = Blueprint('admin', __name__)

@bp.route('/')
@login_required
@role_required('admin')
def index():
    return render_template('admin/index.html')

@bp.route('/users', methods=['GET','POST'])
@login_required
@role_required('admin')
def users():
    db = get_db()
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        role_id = request.form.get('role_id')
        if username and password:
            db.execute('INSERT INTO users(username, password_hash, role_id) VALUES(?,?,?)', (username, generate_password_hash(password), role_id))
            db.commit()
        return redirect(url_for('admin.users'))
    users = db.execute('SELECT u.id, u.username, r.name as role FROM users u LEFT JOIN roles r ON u.role_id = r.id').fetchall()
    roles = db.execute('SELECT id, name FROM roles').fetchall()
    return render_template('admin/users.html', users=users, roles=roles)

@bp.route('/users/update/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_user(user_id):
    db = get_db()
    role_id = request.form.get('role_id')
    password = request.form.get('password','')
    if role_id:
        db.execute('UPDATE users SET role_id=? WHERE id=?', (role_id, user_id))
    if password:
        db.execute('UPDATE users SET password_hash=? WHERE id=?', (generate_password_hash(password), user_id))
    db.commit()
    return redirect(url_for('admin.users'))

@bp.route('/users/delete/<int:user_id>')
@login_required
@role_required('admin')
def delete_user(user_id):
    db = get_db()
    db.execute('DELETE FROM users WHERE id=?', (user_id,))
    db.commit()
    return redirect(url_for('admin.users'))

@bp.route('/roles', methods=['GET','POST'])
@login_required
@role_required('admin')
def roles():
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        desc = request.form.get('desc','')
        if name:
            db.execute('INSERT INTO roles(name, description) VALUES(?,?)', (name, desc))
            db.commit()
        return redirect(url_for('admin.roles'))
    roles = db.execute('SELECT id, name, description FROM roles').fetchall()
    return render_template('admin/roles.html', roles=roles)

@bp.route('/roles/update/<int:role_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_role(role_id):
    db = get_db()
    name = request.form.get('name','').strip()
    desc = request.form.get('desc','')
    if name:
        db.execute('UPDATE roles SET name=?, description=? WHERE id=?', (name, desc, role_id))
        db.commit()
    return redirect(url_for('admin.roles'))

@bp.route('/roles/delete/<int:role_id>')
@login_required
@role_required('admin')
def delete_role(role_id):
    db = get_db()
    db.execute('DELETE FROM roles WHERE id=?', (role_id,))
    db.commit()
    return redirect(url_for('admin.roles'))

@bp.route('/settings', methods=['GET','POST'])
@login_required
def settings():
    db = get_db()
    if request.method == 'POST':
        from flask import session
        if session.get('role') == 'admin':
            app_name = request.form.get('app_name','').strip()
            logo_path = request.form.get('logo_path','').strip()
            row = db.execute('SELECT id FROM settings LIMIT 1').fetchone()
            if row:
                db.execute('UPDATE settings SET app_name=?, logo_path=? WHERE id=?', (app_name, logo_path, row['id']))
            else:
                db.execute('INSERT INTO settings(app_name, logo_path) VALUES(?,?)', (app_name, logo_path))
            db.commit()
        return redirect(url_for('admin.settings'))
    row = get_db().execute('SELECT app_name, logo_path FROM settings LIMIT 1').fetchone()
    return render_template('admin/settings.html', settings=row)

@bp.route('/crawls')
@login_required
def crawls():
    return render_template('admin/crawls.html')

@bp.route('/api/crawl_page')
@login_required
def api_crawl_page():
    from .crawler import crawl_baidu_news
    from flask import jsonify, request
    kw = request.args.get('keyword','').strip()
    pn = request.args.get('pn','0').strip()
    try:
        pn_val = int(pn)
    except Exception:
        pn_val = 0
    if not kw:
        return jsonify({'error':'Keyword required'}), 400
    data = crawl_baidu_news(kw, pn=pn_val)
    return jsonify({'data': data, 'pn': pn_val})

@bp.route('/api/deep_crawl', methods=['POST'])
@login_required
def api_deep_crawl():
    import requests
    from bs4 import BeautifulSoup
    from flask import jsonify, request
    url = request.json.get('url','') if request.is_json else request.form.get('url','')
    if not url:
        return jsonify({'error':'url required'}), 400
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        # naive extraction
        main = soup.find('article') or soup.find('div', class_='content') or soup.find('div', id='content') or soup.body
        text = main.get_text('\n', strip=True) if main else ''
        return jsonify({'content': text[:10000]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/save_items', methods=['POST'])
@login_required
def api_save_items():
    from flask import request, jsonify
    from .db import get_db
    import datetime
    items = []
    if request.is_json:
        items = request.json.get('items', [])
    else:
        # support form
        items = request.form.get('items') or '[]'
        import json
        items = json.loads(items)
    if not isinstance(items, list):
        return jsonify({'error':'items must be list'}), 400
    db = get_db()
    now = datetime.datetime.now().isoformat()
    saved = 0
    for it in items:
        url = (it.get('original_url') or '').strip()
        if not url:
            continue
        exists = db.execute('SELECT 1 FROM crawl_items WHERE original_url=?', (url,)).fetchone()
        if exists:
            continue
        db.execute(
            'INSERT INTO crawl_items(keyword,title,summary,cover,original_url,source,deep_crawled,deep_content,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
            (
                it.get('keyword',''),
                it.get('title',''),
                it.get('summary',''),
                it.get('cover',''),
                url,
                it.get('source',''),
                1 if it.get('deep_crawled') else 0,
                it.get('deep_content',''),
                now
            )
        )
        saved += 1
    db.commit()
    return jsonify({'saved': saved})
