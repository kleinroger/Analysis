from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Role, SystemSetting, Menu
from . import bp
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('需要管理员权限')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@admin_required
def index():
    return render_template('admin/index.html')

@bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    roles = Role.query.all()
    return render_template('admin/users.html', users=users, roles=roles)

@bp.route('/api/users/add', methods=['POST'])
@login_required
@admin_required
def api_users_add():
    data = request.get_json(force=True)
    username = data.get('username')
    password = data.get('password')
    role_id = data.get('role_id')
    
    if not username or not password:
        return jsonify({'code': 1, 'msg': '用户名和密码不能为空'})
    
    if User.query.filter_by(username=username).first():
        return jsonify({'code': 1, 'msg': '用户名已存在'})
    
    user = User(username=username, password=password)
    if role_id:
        user.role_id = int(role_id)
    else:
        # Default to User role if exists
        r = Role.query.filter_by(name='User').first()
        if r:
            user.role = r
            
    db.session.add(user)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '添加成功'})

@bp.route('/api/users/update', methods=['POST'])
@login_required
@admin_required
def api_users_update():
    data = request.get_json(force=True)
    uid = data.get('id')
    username = data.get('username')
    password = data.get('password')
    role_id = data.get('role_id')
    
    user = User.query.get(uid)
    if not user:
        return jsonify({'code': 1, 'msg': '用户不存在'})
    
    if username and username != user.username:
         if User.query.filter_by(username=username).first():
             return jsonify({'code': 1, 'msg': '用户名已存在'})
         user.username = username
    
    if password:
        user.password = password
        
    if role_id:
        user.role_id = int(role_id)
        
    db.session.commit()
    return jsonify({'code': 0, 'msg': '更新成功'})

@bp.route('/api/users/delete', methods=['POST'])
@login_required
@admin_required
def api_users_delete():
    data = request.get_json(force=True)
    uid = data.get('id')
    if uid == current_user.id:
        return jsonify({'code': 1, 'msg': '不能删除自己'})
        
    user = User.query.get(uid)
    if not user:
        return jsonify({'code': 1, 'msg': '用户不存在'})
        
    db.session.delete(user)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '删除成功'})

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        app_name = request.form.get('app_name')
        # app_logo = request.form.get('app_logo') # File upload logic can be added later
        
        setting_name = SystemSetting.query.filter_by(key='app_name').first()
        if not setting_name:
            setting_name = SystemSetting(key='app_name')
            db.session.add(setting_name)
        setting_name.value = app_name
        db.session.commit()
        flash('设置已更新')
        
    app_name = SystemSetting.get_value('app_name', '政企智能舆情分析报告生成智能体应用系统')
    return render_template('admin/settings.html', app_name=app_name)

@bp.route('/menus')
@login_required
@admin_required
def menus():
    return render_template('admin/menus.html')

@bp.route('/api/menus/list')
@login_required
@admin_required
def api_menus_list():
    # Fetch all menus ordered by parent and order
    menus = Menu.query.order_by(Menu.order).all()
    # Flatten structure suitable for TreeTable
    data = []
    for m in menus:
        data.append({
            "id": m.id,
            "name": m.name,
            "icon": m.icon,
            "url": m.url,
            "parentId": m.parent_id if m.parent_id else -1, # TreeTable often likes -1 or 0 for root
            "order": m.order,
            "is_visible": m.is_visible,
            "permission": m.permission
        })
    return jsonify({"code": 0, "msg": "", "count": len(data), "data": data})

@bp.route('/api/menus/add', methods=['POST'])
@login_required
@admin_required
def api_menus_add():
    data = request.get_json(force=True)
    m = Menu(
        name=data.get('name'),
        icon=data.get('icon'),
        url=data.get('url'),
        parent_id=data.get('parentId') if data.get('parentId') != -1 else None,
        order=int(data.get('order', 0)),
        is_visible=bool(data.get('is_visible', True)),
        permission=data.get('permission')
    )
    db.session.add(m)
    db.session.commit()
    return jsonify({"code": 0, "msg": "添加成功"})

@bp.route('/api/menus/update', methods=['POST'])
@login_required
@admin_required
def api_menus_update():
    data = request.get_json(force=True)
    m = Menu.query.get(data.get('id'))
    if not m:
        return jsonify({"code": 1, "msg": "菜单不存在"})
    
    m.name = data.get('name')
    m.icon = data.get('icon')
    m.url = data.get('url')
    # Handle parent change logic carefully (avoid cycle)
    pid = data.get('parentId')
    m.parent_id = pid if pid != -1 else None
    m.order = int(data.get('order', 0))
    m.is_visible = bool(data.get('is_visible', True))
    m.permission = data.get('permission')
    
    db.session.commit()
    return jsonify({"code": 0, "msg": "更新成功"})

@bp.route('/api/menus/delete', methods=['POST'])
@login_required
@admin_required
def api_menus_delete():
    data = request.get_json(force=True)
    mid = data.get('id')
    m = Menu.query.get(mid)
    if not m:
         return jsonify({"code": 1, "msg": "菜单不存在"})
    
    # Check children
    if Menu.query.filter_by(parent_id=mid).count() > 0:
        return jsonify({"code": 1, "msg": "请先删除子菜单"})

    db.session.delete(m)
    db.session.commit()
    return jsonify({"code": 0, "msg": "删除成功"})