from flask import Flask
import os
from .db import init_app as init_db
from .routes import bp
from .auth import bp as auth_bp
from .admin import bp as admin_bp
from .db import get_db

def create_app():
    app = Flask(__name__, static_folder='../static', template_folder='../templates')
    app.config['DATABASE'] = os.path.join(app.root_path, 'app.db')
    app.secret_key = os.environ.get('SECRET_KEY', 'dev')
    init_db(app)
    app.register_blueprint(bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.context_processor
    def inject_settings():
        db = get_db()
        row = db.execute('SELECT app_name, logo_path FROM settings LIMIT 1').fetchone()
        return {
            'app_name': (row['app_name'] if row else '政企智能舆情分析报告生成'),
            'logo_path': (row['logo_path'] if row else None)
        }

    return app
