from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from .db import get_db

bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapped

def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if session.get('role') != role:
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        db = get_db()
        user = db.execute('SELECT id, password_hash, role_id FROM users WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            role = db.execute('SELECT name FROM roles WHERE id = ?', (user['role_id'],)).fetchone()
            session['user_id'] = user['id']
            session['role'] = role['name'] if role else 'user'
            if session['role'] == 'admin':
                return redirect(url_for('admin.index'))
            return redirect(url_for('main.reports'))
        return render_template('login.html', error='用户名或密码错误')
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    username = request.form.get('username','').strip()
    password = request.form.get('password','')
    role_name = request.form.get('role','user')
    if not username or not password:
        return render_template('register.html', error='请输入用户名和密码')
    db = get_db()
    exists = db.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone()
    if exists:
        return render_template('register.html', error='用户名已存在')
    role = db.execute('SELECT id FROM roles WHERE name = ?', (role_name,)).fetchone()
    role_id = role['id'] if role else None
    db.execute('INSERT INTO users(username, password_hash, role_id) VALUES(?,?,?)', (username, generate_password_hash(password), role_id))
    db.commit()
    return redirect(url_for('auth.login'))
