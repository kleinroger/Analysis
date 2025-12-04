import sqlite3
from flask import current_app, g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with current_app.open_resource('../migrations/schema.sql', 'rb') as f:
        db.executescript(f.read().decode('utf-8'))

def init_app(app):
    app.teardown_appcontext(close_db)
    import click

    @app.cli.command('init-db')
    def init_db_command():
        init_db()
        click.echo('initialized')

    @app.cli.command('seed-data')
    def seed_data_command():
        db = get_db()
        db.execute("INSERT OR IGNORE INTO roles(id,name,description) VALUES(1,'admin','管理员'),(2,'user','普通用户')")
        from werkzeug.security import generate_password_hash
        admin = db.execute('SELECT id FROM users WHERE username=?', ('admin',)).fetchone()
        if not admin:
            db.execute('INSERT INTO users(username,password_hash,role_id) VALUES(?,?,?)', ('admin', generate_password_hash('admin123'), 1))
        setting = db.execute('SELECT id FROM settings').fetchone()
        if not setting:
            db.execute('INSERT INTO settings(app_name, logo_path) VALUES(?,?)', ('政企智能舆情分析报告生成', ''))
        sample = db.execute('SELECT id FROM reports LIMIT 1').fetchone()
        if not sample:
            import datetime
            db.execute('INSERT INTO reports(title, body, created_at) VALUES(?,?,?)', ('示例报告', '这是最新报告示例内容', datetime.datetime.now().isoformat()))
        db.commit()
        click.echo('seeded')

    @app.cli.command('set-app-name')
    def set_app_name_command():
        db = get_db()
        name = '政企智能舆情分析报告生成'
        row = db.execute('SELECT id FROM settings LIMIT 1').fetchone()
        if row:
            db.execute('UPDATE settings SET app_name=? WHERE id=?', (name, row['id']))
        else:
            db.execute('INSERT INTO settings(app_name, logo_path) VALUES(?,?)', (name, ''))
        db.commit()
        import click as _click
        _click.echo('app_name set')
