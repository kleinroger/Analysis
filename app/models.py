from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import login_manager
from sqlalchemy.sql import func

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = ['User', 'Admin']
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
                db.session.add(role)
        db.session.commit()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def can(self, permissions):
        # Placeholder for complex permissions, checking role name for now
        return self.role is not None and (self.role.name == 'Admin' or self.role.name == permissions)

    def is_admin(self):
        return self.role is not None and self.role.name == 'Admin'

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.Text)

    @staticmethod
    def get_value(key, default=None):
        setting = SystemSetting.query.filter_by(key=key).first()
        return setting.value if setting else default

class CrawlItem(db.Model):
    __tablename__ = 'crawl_items'
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(128))
    title = db.Column(db.String(256))
    cover = db.Column(db.Text)
    url = db.Column(db.Text)
    source = db.Column(db.String(128))
    deep_crawled = db.Column(db.Boolean, default=False)
    deep_cover = db.Column(db.Text)
    deep_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=func.now())
    
    # Relationship to detail
    detail = db.relationship('ArticleDetail', backref='crawl_item', uselist=False, cascade="all, delete-orphan")

class ArticleDetail(db.Model):
    __tablename__ = 'article_details'
    id = db.Column(db.Integer, primary_key=True)
    crawl_item_id = db.Column(db.Integer, db.ForeignKey('crawl_items.id'), unique=True, nullable=False)
    title = db.Column(db.String(256))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=func.now())

class CrawlRule(db.Model):
    __tablename__ = 'crawl_rules'
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(100))
    title_xpath = db.Column(db.String(500))
    content_xpath = db.Column(db.String(500))
    headers = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "site_name": self.site_name,
            "domain": self.domain,
            "title_xpath": self.title_xpath,
            "content_xpath": self.content_xpath,
            "headers": self.headers,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            "updated_at": self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else ''
        }

class SourceBinding(db.Model):
    __tablename__ = 'source_bindings'
    id = db.Column(db.Integer, primary_key=True)
    source_name = db.Column(db.String(128), nullable=False)
    source_domain = db.Column(db.String(100), nullable=True) # Add domain to distinguish same-named sources
    rule_id = db.Column(db.Integer, db.ForeignKey('crawl_rules.id'), nullable=False)
    
    rule = db.relationship('CrawlRule')
    
    __table_args__ = (
        db.UniqueConstraint('source_name', 'source_domain', 'rule_id', name='unique_source_domain_rule'),
    )

class CrawlSource(db.Model):
    __tablename__ = 'crawl_sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    base_url = db.Column(db.String(300), nullable=False)
    headers = db.Column(db.Text)
    params = db.Column(db.Text)
    pagination = db.Column(db.Text)
    selectors = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "headers": self.headers,
            "params": self.params,
            "pagination": self.pagination,
            "selectors": self.selectors,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            "updated_at": self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else ''
        }

class AIEngine(db.Model):
    __tablename__ = 'ai_engines'
    id = db.Column(db.Integer, primary_key=True)
    provider_name = db.Column(db.String(64), nullable=False) # e.g., OpenAI, Azure
    api_url = db.Column(db.String(256), nullable=False)
    api_key = db.Column(db.String(256), nullable=False)
    model_name = db.Column(db.String(64), nullable=False) # e.g., gpt-4, gpt-3.5-turbo
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "provider_name": self.provider_name,
            "api_url": self.api_url,
            "api_key": self.api_key, # Should be careful returning this, maybe mask it
            "model_name": self.model_name,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            "updated_at": self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else ''
        }

class Menu(db.Model):
    __tablename__ = 'menus'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    icon = db.Column(db.String(64))
    url = db.Column(db.String(128)) # Route name or URL
    parent_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=True)
    order = db.Column(db.Integer, default=0)
    is_visible = db.Column(db.Boolean, default=True)
    permission = db.Column(db.String(64)) # 'Admin', 'User' or None
    
    children = db.relationship('Menu', backref=db.backref('parent', remote_side=[id]), order_by='Menu.order')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'url': self.url,
            'parent_id': self.parent_id,
            'order': self.order,
            'is_visible': self.is_visible,
            'permission': self.permission,
            'children': [c.to_dict() for c in self.children]
        }

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Null for group chat
    content = db.Column(db.Text)
    msg_type = db.Column(db.String(20), default='text')
    created_at = db.Column(db.DateTime, server_default=func.now())
    
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.username if self.sender else 'Unknown',
            'receiver_id': self.receiver_id,
            'content': self.content,
            'msg_type': self.msg_type,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

class AnalysisReport(db.Model):
    __tablename__ = 'analysis_reports'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text, nullable=False) # Markdown content
    report_type = db.Column(db.String(50), default='general') # e.g. 'dashboard', 'cleaning', 'trend'
    created_at = db.Column(db.DateTime, server_default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "report_type": self.report_type,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }
