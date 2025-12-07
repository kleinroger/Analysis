from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import CrawlSource
from . import bp
import json

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            return jsonify({"error": "forbidden"}), 403
        return f(*args, **kwargs)
    return decorated_function

def parse_headers(headers_raw):
    if not headers_raw:
        return ""
    try:
        obj = json.loads(headers_raw)
        if isinstance(obj, dict):
            return json.dumps(obj, ensure_ascii=False)
    except json.JSONDecodeError:
        pass
    headers = {}
    lines = [line.strip() for line in headers_raw.split('\n') if line.strip()]
    cur = None
    for line in lines:
        if line.endswith(':'):
            cur = line[:-1]
        elif cur:
            headers[cur] = line
            cur = None
        elif ':' in line:
            k, v = line.split(':', 1)
            headers[k.strip()] = v.strip()
    return json.dumps(headers, ensure_ascii=False)

@bp.route('/')
@login_required
@admin_required
def index():
    return render_template('crawlers/index.html')

@bp.route('/api/list')
@login_required
@admin_required
def api_list():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    kw = request.args.get('keyword', '', type=str)
    q = CrawlSource.query.order_by(CrawlSource.created_at.desc())
    if kw:
        q = q.filter((CrawlSource.name.contains(kw)) | (CrawlSource.base_url.contains(kw)))
    p = q.paginate(page=page, per_page=limit, error_out=False)
    items = []
    for s in p.items:
        items.append(s.to_dict())
    return jsonify({"code":0, "msg":"", "count": p.total, "data": items})

@bp.route('/api/add', methods=['POST'])
@login_required
@admin_required
def api_add():
    data = request.get_json(force=True) or {}
    name = data.get('name')
    base_url = data.get('base_url')
    if not name or not base_url:
        return jsonify({"code":1, "msg":"name and base_url required"})
    src = CrawlSource(
        name=name,
        base_url=base_url,
        headers=json.dumps(data.get('headers') or {}, ensure_ascii=False) if isinstance(data.get('headers'), dict) else parse_headers(data.get('headers') or ''),
        params=json.dumps(data.get('params') or {}, ensure_ascii=False),
        pagination=json.dumps(data.get('pagination') or {}, ensure_ascii=False),
        selectors=json.dumps(data.get('selectors') or {}, ensure_ascii=False),
        is_active=bool(data.get('is_active', True))
    )
    db.session.add(src)
    db.session.commit()
    return jsonify({"code":0, "msg":"Added"})

@bp.route('/api/update', methods=['POST'])
@login_required
@admin_required
def api_update():
    data = request.get_json(force=True) or {}
    id = data.get('id')
    if not id:
        return jsonify({"code":1, "msg":"id required"})
    s = CrawlSource.query.get(id)
    if not s:
        return jsonify({"code":1, "msg":"not found"})
    s.name = data.get('name', s.name)
    s.base_url = data.get('base_url', s.base_url)
    if 'headers' in data:
        s.headers = json.dumps(data.get('headers') or {}, ensure_ascii=False) if isinstance(data.get('headers'), dict) else parse_headers(data.get('headers') or '')
    if 'params' in data:
        s.params = json.dumps(data.get('params') or {}, ensure_ascii=False)
    if 'pagination' in data:
        s.pagination = json.dumps(data.get('pagination') or {}, ensure_ascii=False)
    if 'selectors' in data:
        s.selectors = json.dumps(data.get('selectors') or {}, ensure_ascii=False)
    if 'is_active' in data:
        s.is_active = bool(data.get('is_active'))
    db.session.commit()
    return jsonify({"code":0, "msg":"Updated"})

@bp.route('/api/delete', methods=['POST'])
@login_required
@admin_required
def api_delete():
    data = request.get_json(force=True) or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({"code":1, "msg":"No ids"})
    CrawlSource.query.filter(CrawlSource.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"code":0, "msg":"Deleted"})

@bp.route('/api/analyze', methods=['POST'])
@login_required
@admin_required
def api_analyze():
    data = request.get_json(force=True) or {}
    url = data.get('url')
    headers_raw = data.get('headers')
    if not url:
        return jsonify({"code":1, "msg":"url required"})
    from urllib.parse import urlparse, parse_qs
    u = urlparse(url)
    base_url = f"{u.scheme}://{u.netloc}{u.path}"
    qs = parse_qs(u.query)
    params = {}
    pagination = {}
    selectors = {}
    keyword_param = None
    for k in qs.keys():
        if k.lower() in ['q','word','keyword']:
            keyword_param = k
            break
    if keyword_param:
        params['keyword_param'] = keyword_param
    for k in qs.keys():
        if k.lower() in ['pn','page','p']:
            try:
                v = int(qs.get(k, ['0'])[0])
            except:
                v = 0
            step = 10 if k.lower() == 'pn' else 1
            pagination = {"param": k, "start": v, "step": step}
            break
    for k, v in qs.items():
        if k != (keyword_param or '') and k != (pagination.get('param') if pagination else ''):
            params[k] = v[0] if isinstance(v, list) and v else ''
    hjson = parse_headers(headers_raw) if headers_raw else json.dumps({}, ensure_ascii=False)
    if 'baidu.com' in u.netloc:
        selectors = {"container": ".result-op", "title": "h3", "link": "h3 a", "source": ".c-color-gray", "image": "img.c-img"}
    return jsonify({"code":0, "data": {"base_url": base_url, "headers": json.loads(hjson) if hjson else {}, "params": params, "pagination": pagination, "selectors": selectors}})

@bp.route('/api/test', methods=['POST'])
@login_required
@admin_required
def api_test():
    from app.crawler import DynamicCrawler
    data = request.get_json(force=True) or {}
    keyword = data.get('keyword') or ''
    config = data.get('config') or {}
    c = DynamicCrawler(config)
    items = c.crawl(keyword, limit=int(data.get('limit', 10)), max_pages=int(data.get('max_pages', 1)))
    return jsonify({"code":0, "data": items})
