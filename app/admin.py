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
    from .crawler import crawl_baidu_news, crawl_sina_news, crawl_sohu_news, crawl_xinhua_multi
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
    elif source == 'sina':
        data = crawl_sina_news(kw, page=(pn_val//10)+1, size=10)
    elif source == 'sohu':
        data = crawl_sohu_news(kw, offset=pn_val, limit=10)
    elif source == 'xinhua':
        data = crawl_xinhua_multi(kw, offset=pn_val, limit=10)
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
        soup = BeautifulSoup(resp.content, 'html.parser')
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
    from .crawler import crawl_baidu_news, crawl_sina_news, crawl_sohu_news, crawl_xinhua_multi
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
    if source == 'baidu':
        cursor = 0
        step = 10
        def fetch():
            return crawl_baidu_news(kw, pn=cursor)
        def advance():
            nonlocal cursor
            cursor += step
        limit = 200
    elif source == 'sina':
        cursor = 0
        step = 10
        def fetch():
            return crawl_sina_news(kw, page=(cursor//10)+1, size=step)
        def advance():
            nonlocal cursor
            cursor += step
        limit = 200
    elif source == 'sohu':
        cursor = 0
        step = 10
        def fetch():
            return crawl_sohu_news(kw, offset=cursor, limit=step)
        def advance():
            nonlocal cursor
            cursor += step
        limit = 200
    elif source == 'xinhua':
        cursor = 0
        step = 10
        def fetch():
            return crawl_xinhua_multi(kw, offset=cursor, limit=step)
        def advance():
            nonlocal cursor
            cursor += step
        limit = 200
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
            soup = BeautifulSoup(resp.content, 'html.parser')
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

@bp.route('/api/warehouse_update/<int:item_id>', methods=['POST'])
@login_required
def api_warehouse_update(item_id):
    from flask import request, jsonify
    db = get_db()
    title = (request.form.get('title') or request.json.get('title') if request.is_json else request.form.get('title')) if request else ''
    summary = (request.form.get('summary') or (request.json.get('summary') if request.is_json else None))
    cover = (request.form.get('cover') or (request.json.get('cover') if request.is_json else None))
    original_url = (request.form.get('original_url') or (request.json.get('original_url') if request.is_json else None))
    source = (request.form.get('source') or (request.json.get('source') if request.is_json else None))
    keyword = (request.form.get('keyword') or (request.json.get('keyword') if request.is_json else None))
    fields = []
    values = []
    if title is not None:
        fields.append('title=?'); values.append(title)
    if summary is not None:
        fields.append('summary=?'); values.append(summary)
    if cover is not None:
        fields.append('cover=?'); values.append(cover)
    if original_url is not None:
        fields.append('original_url=?'); values.append(original_url)
    if source is not None:
        fields.append('source=?'); values.append(source)
    if keyword is not None:
        fields.append('keyword=?'); values.append(keyword)
    if not fields:
        return jsonify({'updated': 0})
    values.append(item_id)
    db.execute(f"UPDATE crawl_items SET {', '.join(fields)} WHERE id=?", values)
    db.commit()
    return jsonify({'updated': 1})

@bp.route('/api/warehouse_analyze/<int:item_id>', methods=['POST'])
@login_required
def api_warehouse_analyze(item_id):
    from flask import jsonify
    db = get_db()
    r = db.execute('SELECT id, title, summary, deep_content FROM crawl_items WHERE id=?', (item_id,)).fetchone()
    if not r:
        return jsonify({'error': 'not found'}), 404
    text = (r['deep_content'] or '') or (r['summary'] or '')
    preview = (text or '')[:400]
    return jsonify({'analysis': 'AI解析入口预留，待实现', 'preview': preview})

@bp.route('/api/warehouse_delete/<int:item_id>', methods=['POST'])
@login_required
def api_warehouse_delete(item_id):
    from flask import jsonify
    db = get_db()
    db.execute('DELETE FROM crawl_items WHERE id=?', (item_id,))
    db.commit()
    return jsonify({'deleted': 1})

@bp.route('/rulelib')
@login_required
@role_required('admin')
def rulelib():
    return render_template('admin/rulelib.html')

@bp.route('/api/rulelib_items')
@login_required
@role_required('admin')
def api_rulelib_items():
    from flask import jsonify, request
    import json
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
        total = db.execute('SELECT COUNT(1) AS cnt FROM crawl_rules WHERE site LIKE ? OR domain LIKE ?', (f'%{q}%', f'%{q}%')).fetchone()['cnt']
        rows = db.execute('SELECT id,site,domain,title_xpath,content_xpath,headers,created_at,updated_at FROM crawl_rules WHERE site LIKE ? OR domain LIKE ? ORDER BY (updated_at IS NULL), updated_at DESC, id DESC LIMIT ? OFFSET ?', (f'%{q}%', f'%{q}%', limit, offset)).fetchall()
    else:
        total = db.execute('SELECT COUNT(1) AS cnt FROM crawl_rules').fetchone()['cnt']
        rows = db.execute('SELECT id,site,domain,title_xpath,content_xpath,headers,created_at,updated_at FROM crawl_rules ORDER BY (updated_at IS NULL), updated_at DESC, id DESC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
    items = []
    for r in rows:
        h = r['headers'] or ''
        upd = r['updated_at'] or ''
        if upd:
            s = str(upd).replace('T', ' ')
            if len(s) >= 16:
                upd = s[:16]
            else:
                upd = s
        items.append({
            'id': r['id'],
            'site': r['site'],
            'domain': r['domain'] or '',
            'title_xpath': r['title_xpath'] or '',
            'content_xpath': r['content_xpath'] or '',
            'headers': h,
            'created_at': r['created_at'] or '',
            'updated_at': upd
        })
    return jsonify({'items': items, 'total': total, 'page': page, 'limit': limit})

@bp.route('/api/rulelib_create', methods=['POST'])
@login_required
@role_required('admin')
def api_rulelib_create():
    from flask import request, jsonify
    import datetime, json
    db = get_db()
    data = request.json if request.is_json else request.form
    site = (data.get('site') or '').strip()
    domain = (data.get('domain') or '').strip()
    title_xpath = (data.get('title_xpath') or '').strip()
    content_xpath = (data.get('content_xpath') or '').strip()
    headers = data.get('headers') or ''
    if not site:
        return jsonify({'error':'site required'}), 400
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    db.execute('INSERT INTO crawl_rules(site,domain,title_xpath,content_xpath,headers,created_at,updated_at) VALUES(?,?,?,?,?,?,?)', (site, domain, title_xpath, content_xpath, headers, now, now))
    db.commit()
    return jsonify({'created': 1})

@bp.route('/api/rulelib_update/<int:rule_id>', methods=['POST'])
@login_required
@role_required('admin')
def api_rulelib_update(rule_id):
    from flask import request, jsonify
    import datetime
    db = get_db()
    data = request.json if request.is_json else request.form
    fields = []
    values = []
    for key in ['site','domain','title_xpath','content_xpath','headers']:
        val = data.get(key)
        if val is not None:
            fields.append(f"{key}=?")
            values.append(val)
    if not fields:
        return jsonify({'updated': 0})
    values.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    fields.append('updated_at=?')
    values.append(rule_id)
    db.execute(f"UPDATE crawl_rules SET {', '.join(fields)} WHERE id=?", values)
    db.commit()
    return jsonify({'updated': 1})

@bp.route('/api/rulelib_delete/<int:rule_id>', methods=['POST'])
@login_required
@role_required('admin')
def api_rulelib_delete(rule_id):
    from flask import jsonify
    db = get_db()
    db.execute('DELETE FROM crawl_rules WHERE id=?', (rule_id,))
    db.commit()
    return jsonify({'deleted': 1})

@bp.route('/ai_engines')
@login_required
@role_required('admin')
def ai_engines():
    return render_template('admin/ai_engines.html')

@bp.route('/api/ai_engines_items')
@login_required
@role_required('admin')
def api_ai_engines_items():
    from flask import jsonify, request
    db = get_db()
    try:
        page = int(request.args.get('page', '1'))
        limit = int(request.args.get('limit', '12'))
    except Exception:
        page, limit = 1, 12
    q = (request.args.get('q','') or '').strip()
    if limit < 1:
        limit = 12
    if limit > 100:
        limit = 100
    offset = (page - 1) * limit
    if q:
        total = db.execute('SELECT COUNT(1) AS cnt FROM ai_engines WHERE provider LIKE ? OR model_name LIKE ?', (f'%{q}%', f'%{q}%')).fetchone()['cnt']
        rows = db.execute('SELECT id,provider,api_url,model_name,description,created_at,updated_at FROM ai_engines WHERE provider LIKE ? OR model_name LIKE ? ORDER BY (updated_at IS NULL), updated_at DESC, id DESC LIMIT ? OFFSET ?', (f'%{q}%', f'%{q}%', limit, offset)).fetchall()
    else:
        total = db.execute('SELECT COUNT(1) AS cnt FROM ai_engines').fetchone()['cnt']
        rows = db.execute('SELECT id,provider,api_url,model_name,description,created_at,updated_at FROM ai_engines ORDER BY (updated_at IS NULL), updated_at DESC, id DESC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
    items = []
    for r in rows:
        upd = r['updated_at'] or ''
        if upd:
            s = str(upd).replace('T', ' ')
            if len(s) >= 16:
                upd = s[:16]
            else:
                upd = s
        items.append({
            'id': r['id'],
            'provider': r['provider'],
            'api_url': r['api_url'] or '',
            'model_name': r['model_name'] or '',
            'description': r['description'] or '',
            'updated_at': upd
        })
    return jsonify({'items': items, 'total': total, 'page': page, 'limit': limit})

@bp.route('/api/ai_engines_get/<int:engine_id>')
@login_required
@role_required('admin')
def api_ai_engines_get(engine_id):
    from flask import jsonify
    db = get_db()
    row = db.execute('SELECT id,provider,api_url,api_key,model_name,description,created_at,updated_at FROM ai_engines WHERE id=?', (engine_id,)).fetchone()
    if not row:
        return jsonify({'error':'not found'}), 404
    return jsonify({
        'id': row['id'],
        'provider': row['provider'],
        'api_url': row['api_url'] or '',
        'api_key': row['api_key'] or '',
        'model_name': row['model_name'] or '',
        'description': row['description'] or '',
        'created_at': row['created_at'] or '',
        'updated_at': row['updated_at'] or ''
    })

@bp.route('/api/ai_engines_create', methods=['POST'])
@login_required
@role_required('admin')
def api_ai_engines_create():
    from flask import request, jsonify
    import datetime
    db = get_db()
    data = request.json if request.is_json else request.form
    provider = (data.get('provider') or '').strip()
    api_url = (data.get('api_url') or '').strip()
    api_key = (data.get('api_key') or '').strip()
    model_name = (data.get('model_name') or '').strip()
    description = (data.get('description') or '').strip()
    if not provider or not api_url or not model_name:
        return jsonify({'error':'missing required'}), 400
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    db.execute('INSERT INTO ai_engines(provider,api_url,api_key,model_name,description,created_at,updated_at) VALUES(?,?,?,?,?,?,?)', (provider, api_url, api_key, model_name, description, now, now))
    db.commit()
    return jsonify({'created': 1})

@bp.route('/api/ai_engines_update/<int:engine_id>', methods=['POST'])
@login_required
@role_required('admin')
def api_ai_engines_update(engine_id):
    from flask import request, jsonify
    import datetime
    db = get_db()
    data = request.json if request.is_json else request.form
    fields = []
    values = []
    for key in ['provider','api_url','api_key','model_name','description']:
        val = data.get(key)
        if val is not None:
            fields.append(f"{key}=?")
            values.append(val)
    if not fields:
        return jsonify({'updated': 0})
    values.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    fields.append('updated_at=?')
    values.append(engine_id)
    db.execute(f"UPDATE ai_engines SET {', '.join(fields)} WHERE id=?", values)
    db.commit()
    return jsonify({'updated': 1})

@bp.route('/api/ai_engines_delete/<int:engine_id>', methods=['POST'])
@login_required
@role_required('admin')
def api_ai_engines_delete(engine_id):
    from flask import jsonify
    db = get_db()
    db.execute('DELETE FROM ai_engines WHERE id=?', (engine_id,))
    db.commit()
    return jsonify({'deleted': 1})

# AI Assistants
@bp.route('/ai_assistants')
@login_required
@role_required('admin')
def ai_assistants():
    return render_template('admin/ai_assistants.html')

@bp.route('/ai_assistants/<int:assistant_id>')
@login_required
@role_required('admin')
def ai_assistants_chat_page(assistant_id):
    return render_template('admin/ai_chat.html', assistant_id=assistant_id)

@bp.route('/api/ai_assistants_items')
@login_required
@role_required('admin')
def api_ai_assistants_items():
    from flask import jsonify, request
    db = get_db()
    try:
        page = int(request.args.get('page', '1'))
        limit = int(request.args.get('limit', '12'))
    except Exception:
        page, limit = 1, 12
    q = (request.args.get('q','') or '').strip()
    if limit < 1:
        limit = 12
    if limit > 100:
        limit = 100
    offset = (page - 1) * limit
    if q:
        total = db.execute('SELECT COUNT(1) AS cnt FROM ai_assistants WHERE name LIKE ?', (f'%{q}%',)).fetchone()['cnt']
        rows = db.execute('SELECT a.id,a.name,a.engine_id,a.system_prompt,a.created_at,a.updated_at,e.provider,e.model_name FROM ai_assistants a LEFT JOIN ai_engines e ON a.engine_id=e.id WHERE a.name LIKE ? ORDER BY (a.updated_at IS NULL), a.updated_at DESC, a.id DESC LIMIT ? OFFSET ?', (f'%{q}%', limit, offset)).fetchall()
    else:
        total = db.execute('SELECT COUNT(1) AS cnt FROM ai_assistants').fetchone()['cnt']
        rows = db.execute('SELECT a.id,a.name,a.engine_id,a.system_prompt,a.created_at,a.updated_at,e.provider,e.model_name FROM ai_assistants a LEFT JOIN ai_engines e ON a.engine_id=e.id ORDER BY (a.updated_at IS NULL), a.updated_at DESC, a.id DESC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
    items = []
    for r in rows:
        upd = r['updated_at'] or ''
        if upd:
            s = str(upd).replace('T', ' ')
            upd = s[:16] if len(s) >= 16 else s
        items.append({
            'id': r['id'],
            'name': r['name'],
            'engine_id': r['engine_id'],
            'provider': r['provider'] or '',
            'model_name': r['model_name'] or '',
            'updated_at': upd,
            'system_prompt': r['system_prompt'] or ''
        })
    return jsonify({'items': items, 'total': total, 'page': page, 'limit': limit})

@bp.route('/api/ai_assistants_get/<int:assistant_id>')
@login_required
@role_required('admin')
def api_ai_assistants_get(assistant_id):
    from flask import jsonify
    db = get_db()
    row = db.execute('SELECT id,name,engine_id,system_prompt,created_at,updated_at FROM ai_assistants WHERE id=?', (assistant_id,)).fetchone()
    if not row:
        return jsonify({'error':'not found'}), 404
    return jsonify({
        'id': row['id'],
        'name': row['name'],
        'engine_id': row['engine_id'],
        'system_prompt': row['system_prompt'] or '',
        'created_at': row['created_at'] or '',
        'updated_at': row['updated_at'] or ''
    })

@bp.route('/api/ai_assistants_create', methods=['POST'])
@login_required
@role_required('admin')
def api_ai_assistants_create():
    from flask import request, jsonify
    import datetime
    db = get_db()
    data = request.json if request.is_json else request.form
    name = (data.get('name') or '').strip()
    engine_id = data.get('engine_id')
    prompt = (data.get('system_prompt') or '').strip()
    try:
        engine_id = int(engine_id)
    except Exception:
        return jsonify({'error':'invalid engine_id'}), 400
    if not name:
        return jsonify({'error':'name required'}), 400
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    db.execute('INSERT INTO ai_assistants(name,engine_id,system_prompt,created_at,updated_at) VALUES(?,?,?,?,?)', (name, engine_id, prompt, now, now))
    db.commit()
    return jsonify({'created': 1})

@bp.route('/api/ai_assistants_update/<int:assistant_id>', methods=['POST'])
@login_required
@role_required('admin')
def api_ai_assistants_update(assistant_id):
    from flask import request, jsonify
    import datetime
    db = get_db()
    data = request.json if request.is_json else request.form
    fields = []
    values = []
    for key in ['name','engine_id','system_prompt']:
        val = data.get(key)
        if val is not None:
            fields.append(f"{key}=?")
            values.append(val)
    if not fields:
        return jsonify({'updated': 0})
    values.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    fields.append('updated_at=?')
    values.append(assistant_id)
    db.execute(f"UPDATE ai_assistants SET {', '.join(fields)} WHERE id=?", values)
    db.commit()
    return jsonify({'updated': 1})

@bp.route('/api/ai_assistants_delete/<int:assistant_id>', methods=['POST'])
@login_required
@role_required('admin')
def api_ai_assistants_delete(assistant_id):
    from flask import jsonify
    db = get_db()
    db.execute('DELETE FROM ai_messages WHERE assistant_id=?', (assistant_id,))
    db.execute('DELETE FROM ai_assistants WHERE id=?', (assistant_id,))
    db.commit()
    return jsonify({'deleted': 1})

@bp.route('/api/ai_assistants_chat/<int:assistant_id>', methods=['POST'])
@login_required
@role_required('admin')
def api_ai_assistants_chat(assistant_id):
    from flask import request, jsonify
    import datetime, requests, json
    db = get_db()
    assistant = db.execute('SELECT id,name,engine_id,system_prompt FROM ai_assistants WHERE id=?', (assistant_id,)).fetchone()
    if not assistant:
        return jsonify({'error':'assistant not found'}), 404
    engine = db.execute('SELECT id,provider,api_url,api_key,model_name FROM ai_engines WHERE id=?', (assistant['engine_id'],)).fetchone()
    if not engine:
        return jsonify({'error':'engine not found'}), 404
    text = (request.json.get('text') if request.is_json else request.form.get('text')) or ''
    text = text.strip()
    if not text:
        return jsonify({'error':'text required'}), 400
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    db.execute('INSERT INTO ai_messages(assistant_id,role,content,created_at) VALUES(?,?,?,?)', (assistant_id, 'user', text, now))
    db.commit()
    rows = db.execute('SELECT role, content FROM ai_messages WHERE assistant_id=? ORDER BY id DESC LIMIT 20', (assistant_id,)).fetchall()
    history = [{'role': r['role'], 'content': r['content']} for r in reversed(rows)]
    messages = []
    if assistant['system_prompt']:
        messages.append({'role':'system','content': assistant['system_prompt']})
    messages.extend(history)
    endpoint = (engine['api_url'] or '').rstrip('/') + '/chat/completions'
    payload = {
        'model': engine['model_name'],
        'messages': messages,
        'temperature': 0.7,
        'stream': False
    }
    headers = {'Content-Type': 'application/json'}
    if engine['api_key']:
        headers['Authorization'] = 'Bearer ' + engine['api_key']
    try:
        resp = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        content = ''
        try:
            content = data['choices'][0]['message']['content']
        except Exception:
            content = json.dumps(data, ensure_ascii=False)
    except Exception as e:
        content = '调用失败: ' + str(e)
    db.execute('INSERT INTO ai_messages(assistant_id,role,content,created_at) VALUES(?,?,?,?)', (assistant_id, 'assistant', content, now))
    db.commit()
    return jsonify({'reply': content})
