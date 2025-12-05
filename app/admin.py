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
    from .crawler import crawl_baidu_news, crawl_xinhua_news
    from flask import jsonify, request
    kw = request.args.get('keyword','').strip()
    pn = request.args.get('pn','0').strip()
    source = (request.args.get('source','baidu') or 'baidu').strip()
    try:
        pn_val = int(pn)
    except Exception:
        pn_val = 0
    if not kw:
        return jsonify({'error':'Keyword required'}), 400
    if source == 'baidu':
        data = crawl_baidu_news(kw, pn=pn_val)
    elif source == 'xinhua':
        page = max(1, int(pn_val/10)+1)
        data = crawl_xinhua_news(kw, page=page)
    else:
        return jsonify({'error':'Unknown source'}), 400
    return jsonify({'data': data, 'pn': pn_val, 'source': source})

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
            'INSERT INTO crawl_items(keyword,title,summary,cover,original_url,source,deep_crawled,deep_content,detail_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
            (
                it.get('keyword',''),
                it.get('title',''),
                it.get('summary',''),
                it.get('cover',''),
                url,
                it.get('source',''),
                1 if it.get('deep_crawled') else 0,
                it.get('deep_content',''),
                it.get('detail_json','') or '{}',
                now
            )
        )
        saved += 1
    db.commit()
    return jsonify({'saved': saved})

@bp.route('/api/crawl_auto', methods=['POST'])
@login_required
def api_crawl_auto():
    from flask import request, jsonify
    from .crawler import crawl_baidu_news, crawl_xinhua_news
    from .db import get_db
    import datetime, json, requests
    from bs4 import BeautifulSoup
    kw = ''
    num = 10
    source = 'baidu'
    if request.is_json:
        kw = (request.json.get('keyword','') or '').strip()
        try:
            num = int(request.json.get('num','10'))
        except Exception:
            num = 10
        src = (request.json.get('source','baidu') or 'baidu').strip()
        source = src
    else:
        kw = (request.form.get('keyword','') or '').strip()
        try:
            num = int(request.form.get('num','10'))
        except Exception:
            num = 10
        src = (request.form.get('source','baidu') or 'baidu').strip()
        source = src
    if not kw:
        return jsonify({'error':'Keyword required'}), 400
    if num < 1:
        num = 1
    if num > 100:
        num = 100
    db = get_db()
    aggregated = []
    seen = set()
    # Iterate pages depending on source
    if source == 'baidu':
        cursor = 0
        step = 10
        def fetch():
            return crawl_baidu_news(kw, pn=cursor)
        def advance():
            nonlocal cursor
            cursor += step
        limit = 200
    elif source == 'xinhua':
        cursor = 1
        step = 1
        def fetch():
            return crawl_xinhua_news(kw, page=cursor)
        def advance():
            nonlocal cursor
            cursor += step
        limit = 50
    else:
        return jsonify({'error':'Unknown source'}), 400
    while len(aggregated) < num and cursor <= limit:
        page = fetch()
        if not page:
            break
        for it in page:
            url = (it.get('original_url') or '').strip()
            if not url or url in seen or not it.get('cover') or not it.get('title'):
                continue
            seen.add(url)
            it['keyword'] = kw
            aggregated.append(it)
            if len(aggregated) >= num:
                break
        advance()
    now = datetime.datetime.now().isoformat()
    saved = 0
    for it in aggregated:
        url = (it.get('original_url') or '').strip()
        if not url or not it.get('cover') or not it.get('title'):
            continue
        exists = db.execute('SELECT 1 FROM crawl_items WHERE original_url=?', (url,)).fetchone()
        if exists:
            continue
        content = ''
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            main = soup.find('article') or soup.find('div', class_='content') or soup.find('div', id='content') or soup.body
            content = main.get_text('\n', strip=True)[:10000] if main else ''
        except Exception:
            content = ''
        details = {'content_length': len(content)}
        db.execute(
            'INSERT INTO crawl_items(keyword,title,summary,cover,original_url,source,deep_crawled,deep_content,detail_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
            (
                it.get('keyword',''),
                it.get('title',''),
                it.get('summary',''),
                it.get('cover',''),
                url,
                it.get('source',''),
                1 if content else 0,
                content,
                json.dumps(details, ensure_ascii=False),
                now
            )
        )
        saved += 1
    db.commit()
    return jsonify({'saved': saved, 'requested': num, 'keyword': kw, 'items': len(aggregated), 'source': source})

@bp.route('/warehouse')
@login_required
def warehouse():
    return render_template('admin/warehouse.html')

@bp.route('/api/warehouse_items')
@login_required
def api_warehouse_items():
    from flask import jsonify, request
    db = get_db()
    try:
        page = int(request.args.get('page', '1'))
        limit = int(request.args.get('limit', '10'))
    except Exception:
        page, limit = 1, 10
    q = (request.args.get('q','') or '').strip()
    if limit < 1:
        limit = 10
    if limit > 100:
        limit = 100
    offset = (page - 1) * limit
    if q:
        total = db.execute('SELECT COUNT(1) AS cnt FROM crawl_items WHERE title LIKE ? OR keyword LIKE ?', (f'%{q}%', f'%{q}%')).fetchone()['cnt']
        rows = db.execute('SELECT id,keyword,title,summary,cover,original_url,source,deep_crawled,created_at FROM crawl_items WHERE title LIKE ? OR keyword LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?', (f'%{q}%', f'%{q}%', limit, offset)).fetchall()
    else:
        total = db.execute('SELECT COUNT(1) AS cnt FROM crawl_items').fetchone()['cnt']
        rows = db.execute('SELECT id,keyword,title,summary,cover,original_url,source,deep_crawled,created_at FROM crawl_items ORDER BY created_at DESC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
    items = []
    for r in rows:
        items.append({
            'id': r['id'],
            'keyword': r['keyword'],
            'title': r['title'],
            'summary': r['summary'],
            'cover': r['cover'],
            'original_url': r['original_url'],
            'source': r['source'],
            'deep_crawled': bool(r['deep_crawled']),
            'created_at': r['created_at']
        })
    return jsonify({'items': items, 'total': total, 'page': page, 'limit': limit})

@bp.route('/api/warehouse_item/<int:item_id>')
@login_required
def api_warehouse_item(item_id):
    from flask import jsonify
    db = get_db()
    r = db.execute('SELECT id,keyword,title,summary,cover,original_url,source,deep_crawled,deep_content,detail_json,created_at FROM crawl_items WHERE id=?', (item_id,)).fetchone()
    if not r:
        return jsonify({'error':'not found'}), 404
    return jsonify({
        'id': r['id'],
        'keyword': r['keyword'],
        'title': r['title'],
        'summary': r['summary'],
        'cover': r['cover'],
        'original_url': r['original_url'],
        'source': r['source'],
        'deep_crawled': bool(r['deep_crawled']),
        'deep_content': r['deep_content'] or '',
        'detail_json': r['detail_json'] or '{}',
        'created_at': r['created_at']
    })

@bp.route('/api/warehouse_delete/<int:item_id>', methods=['POST'])
@login_required
def api_warehouse_delete(item_id):
    from flask import jsonify
    db = get_db()
    db.execute('DELETE FROM crawl_items WHERE id=?', (item_id,))
    db.commit()
    return jsonify({'deleted': 1})
