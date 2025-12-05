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

    @app.cli.command('migrate-db')
    def migrate_db_command():
        init_db()
        db = get_db()
        def has_column(table, name):
            rows = db.execute(f"PRAGMA table_info({table})").fetchall()
            for r in rows:
                if r['name'] == name:
                    return True
            return False
        if not has_column('crawl_items', 'deep_crawled'):
            db.execute("ALTER TABLE crawl_items ADD COLUMN deep_crawled INTEGER DEFAULT 0")
        if not has_column('crawl_items', 'deep_content'):
            db.execute("ALTER TABLE crawl_items ADD COLUMN deep_content TEXT")
        if not has_column('crawl_items', 'detail_json'):
            db.execute("ALTER TABLE crawl_items ADD COLUMN detail_json TEXT")
        db.commit()
        click.echo('migrated')

    @app.cli.command('add-ai-engine')
    @click.option('--provider', required=True)
    @click.option('--api-url', required=True)
    @click.option('--api-key', required=False)
    @click.option('--model-name', required=True)
    @click.option('--description', required=False, default='')
    def add_ai_engine(provider, api_url, api_key, model_name, description):
        db = get_db()
        import datetime
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        provider = (provider or '').strip()
        api_url = (api_url or '').strip()
        api_key = (api_key or '').strip()
        model_name = (model_name or '').strip()
        description = (description or '').strip()
        row = db.execute('SELECT id FROM ai_engines WHERE provider=? AND model_name=?', (provider, model_name)).fetchone()
        if row:
            db.execute('UPDATE ai_engines SET api_url=?, api_key=?, description=?, updated_at=? WHERE id=?', (api_url, api_key, description, now, row['id']))
        else:
            db.execute('INSERT INTO ai_engines(provider,api_url,api_key,model_name,description,created_at,updated_at) VALUES(?,?,?,?,?,?,?)', (provider, api_url, api_key, model_name, description, now, now))
        db.commit()
        click.echo('ok')
