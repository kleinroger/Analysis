from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Role
from app import db
from . import bp

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user is not None and user.verify_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        flash('无效的用户名或密码')
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not password:
             flash('用户名和密码不能为空')
             return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
            return render_template('auth/register.html')
        
        # Assign default role 'User'
        user_role = Role.query.filter_by(name='User').first()
        # If roles table is empty, we might want to insert roles, but let's assume it's initialized
        
        user = User(username=username, password=password, role=user_role)
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')