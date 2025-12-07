from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import AIEngine
from . import bp

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            return jsonify({"error": "forbidden"}), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@admin_required
def index():
    return render_template('ai_engine/index.html')

@bp.route('/api/list')
@login_required
@admin_required
def api_list():
    engines = AIEngine.query.order_by(AIEngine.created_at.desc()).all()
    return jsonify({
        "code": 0,
        "data": [e.to_dict() for e in engines]
    })

@bp.route('/api/add', methods=['POST'])
@login_required
@admin_required
def api_add():
    data = request.get_json(force=True) or {}
    provider_name = data.get('provider_name')
    api_url = data.get('api_url')
    api_key = data.get('api_key')
    model_name = data.get('model_name')
    
    if not all([provider_name, api_url, api_key, model_name]):
        return jsonify({"code": 1, "msg": "Missing required fields"})
        
    engine = AIEngine(
        provider_name=provider_name,
        api_url=api_url,
        api_key=api_key,
        model_name=model_name
    )
    
    try:
        db.session.add(engine)
        db.session.commit()
        return jsonify({"code": 0, "msg": "Added successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "msg": str(e)})

@bp.route('/api/update', methods=['POST'])
@login_required
@admin_required
def api_update():
    data = request.get_json(force=True) or {}
    id = data.get('id')
    if not id:
        return jsonify({"code": 1, "msg": "No id provided"})
        
    engine = AIEngine.query.get(id)
    if not engine:
        return jsonify({"code": 1, "msg": "Engine not found"})
        
    if 'provider_name' in data: engine.provider_name = data['provider_name']
    if 'api_url' in data: engine.api_url = data['api_url']
    if 'api_key' in data: engine.api_key = data['api_key']
    if 'model_name' in data: engine.model_name = data['model_name']
    if 'is_active' in data: engine.is_active = data['is_active']
    
    try:
        db.session.commit()
        return jsonify({"code": 0, "msg": "Updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "msg": str(e)})

@bp.route('/api/delete', methods=['POST'])
@login_required
@admin_required
def api_delete():
    data = request.get_json(force=True) or {}
    id = data.get('id')
    if not id:
        return jsonify({"code": 1, "msg": "No id provided"})
        
    try:
        AIEngine.query.filter_by(id=id).delete()
        db.session.commit()
        return jsonify({"code": 0, "msg": "Deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "msg": str(e)})

@bp.route('/api/chat_test', methods=['POST'])
@login_required
@admin_required
def api_chat_test():
    import requests
    data = request.get_json(force=True) or {}
    id = data.get('id')
    message = data.get('message')
    
    if not id or not message:
        return jsonify({"code": 1, "msg": "Missing parameters"})
        
    engine = AIEngine.query.get(id)
    if not engine:
        return jsonify({"code": 1, "msg": "Engine not found"})
        
    # Construct URL
    # If user entered full path ending in chat/completions, use it
    # Otherwise assume it's base URL and append /chat/completions
    url = engine.api_url.strip().rstrip('/')
    if not url.endswith('/chat/completions'):
        url += '/chat/completions'
        
    headers = {
        "Authorization": f"Bearer {engine.api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": engine.model_name,
        "messages": [{"role": "user", "content": message}]
    }
    
    try:
        # Set timeout to 60s for slow models
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        if response.status_code == 200:
            res_data = response.json()
            # Try to extract content from standard OpenAI format
            try:
                content = res_data['choices'][0]['message']['content']
                return jsonify({"code": 0, "data": content})
            except:
                # If structure is different, return full response text or json
                return jsonify({"code": 0, "data": str(res_data)}) 
        else:
            return jsonify({"code": 1, "msg": f"API Error {response.status_code}: {response.text}"})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})
