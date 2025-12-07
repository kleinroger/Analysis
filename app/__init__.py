import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_socketio import SocketIO

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
socketio = SocketIO()
login_manager.login_view = 'auth.login'

def create_app():
    if getattr(sys, 'frozen', False):
        # Running in a bundle
        bundle_dir = sys._MEIPASS
        template_folder = os.path.join(bundle_dir, 'templates')
        static_folder = os.path.join(bundle_dir, 'static')
        # DB file should be in the same directory as the executable
        db_file = os.path.join(os.path.dirname(sys.executable), 'app.db')
    else:
        # Running in a normal Python environment
        base_dir = os.path.dirname(__file__)
        template_folder = os.path.join(base_dir, '..', 'templates')
        static_folder = os.path.join(base_dir, '..', 'static')
        db_file = os.path.join(base_dir, '..', 'app.db')

    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_file}')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(app, manage_session=False, cors_allowed_origins="*")

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from .admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from .collect import bp as collect_bp
    app.register_blueprint(collect_bp, url_prefix='/collect')

    from .warehouse import bp as warehouse_bp
    app.register_blueprint(warehouse_bp, url_prefix='/warehouse')

    from .rules import bp as rules_bp
    app.register_blueprint(rules_bp, url_prefix='/rules')

    from .ai_engine import bp as ai_engine_bp
    app.register_blueprint(ai_engine_bp, url_prefix='/ai_engine')

    from .crawler_mgmt import bp as crawler_mgmt_bp
    app.register_blueprint(crawler_mgmt_bp, url_prefix='/crawler_mgmt')

    from .ai_analysis import bp as ai_analysis_bp
    app.register_blueprint(ai_analysis_bp, url_prefix='/ai_analysis')

    from .dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    from .reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')

    from .chat import bp as chat_bp
    app.register_blueprint(chat_bp, url_prefix='/chat')

    @app.context_processor
    def inject_menus():
        from .models import Menu
        from flask_login import current_user
        if not current_user.is_authenticated:
            return dict(sidebar_menus=[])
        
        # Get root menus
        # Note: We fetch all and filter in memory or join if needed, but simple query for roots is fine
        # SQLAlchemy relationships will handle children loading
        menus = Menu.query.filter_by(parent_id=None, is_visible=True).order_by(Menu.order).all()
        return dict(sidebar_menus=menus)

    with app.app_context():
        from . import models
        # Create tables is handled by migrate, but for dev we can check
        pass

    return app
