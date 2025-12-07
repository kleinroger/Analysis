from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import CrawlRule
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
    """
    Parse headers string into JSON string.
    Handles both JSON string and raw headers text.
    """
    if not headers_raw:
        return ""
        
    # Try to parse as JSON first
    try:
        json_obj = json.loads(headers_raw)
        if isinstance(json_obj, dict):
            return json.dumps(json_obj, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        pass
        
    # Parse as raw text
    headers = {}
    lines = [line.strip() for line in headers_raw.split('\n') if line.strip()]
    current_key = None
    
    for line in lines:
        if line.endswith(':'):
            current_key = line[:-1]
        elif current_key:
            headers[current_key] = line
            current_key = None
        elif ':' in line:
            parts = line.split(':', 1)
            key = parts[0].strip()
            val = parts[1].strip()
            headers[key] = val
            
    return json.dumps(headers, indent=2, ensure_ascii=False)

@bp.route('/')
@login_required
@admin_required
def index():
    return render_template('rules/index.html')


@bp.route('/api/list')
@login_required
@admin_required
def api_list():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    pagination = CrawlRule.query.order_by(CrawlRule.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)
    
    items = [item.to_dict() for item in pagination.items]
        
    return jsonify({
        "code": 0,
        "msg": "",
        "count": pagination.total,
        "data": items
    })

@bp.route('/api/add', methods=['POST'])
@login_required
@admin_required
def api_add():
    data = request.get_json(force=True) or {}
    site_name = data.get('site_name')
    if not site_name:
        return jsonify({"code": 1, "msg": "Site name is required"})
        
    rule = CrawlRule(
        site_name=site_name,
        domain=data.get('domain'),
        title_xpath=data.get('title_xpath'),
        content_xpath=data.get('content_xpath'),
        headers=parse_headers(data.get('headers'))
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify({"code": 0, "msg": "Added successfully"})

@bp.route('/api/update', methods=['POST'])
@login_required
@admin_required
def api_update():
    data = request.get_json(force=True) or {}
    id = data.get('id')
    if not id:
        return jsonify({"code": 1, "msg": "ID is required"})
        
    rule = CrawlRule.query.get(id)
    if not rule:
        return jsonify({"code": 1, "msg": "Rule not found"})
        
    rule.site_name = data.get('site_name', rule.site_name)
    rule.domain = data.get('domain', rule.domain)
    rule.title_xpath = data.get('title_xpath', rule.title_xpath)
    rule.content_xpath = data.get('content_xpath', rule.content_xpath)
    if 'headers' in data:
        rule.headers = parse_headers(data.get('headers'))
    
    db.session.commit()
    return jsonify({"code": 0, "msg": "Updated successfully"})

@bp.route('/api/delete', methods=['POST'])
@login_required
@admin_required
def api_delete():
    data = request.get_json(force=True) or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({"code": 1, "msg": "No ids provided"})
    
    CrawlRule.query.filter(CrawlRule.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"code": 0, "msg": "Deleted successfully"})

@bp.route('/api/copy', methods=['POST'])
@login_required
@admin_required
def api_copy():
    data = request.get_json(force=True) or {}
    id = data.get('id')
    if not id:
        return jsonify({"code": 1, "msg": "ID is required"})
        
    rule = CrawlRule.query.get(id)
    if not rule:
        return jsonify({"code": 1, "msg": "Rule not found"})
    
    # Create copy
    new_rule = CrawlRule(
        site_name=f"{rule.site_name} - 副本",
        domain=rule.domain,
        title_xpath=rule.title_xpath,
        content_xpath=rule.content_xpath,
        headers=rule.headers
    )
    
    db.session.add(new_rule)
    db.session.commit()
    return jsonify({"code": 0, "msg": "Copied successfully"})
