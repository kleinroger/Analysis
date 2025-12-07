from app import create_app, db
from app.models import Role, User

app = create_app()

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Database tables created successfully!")
    
    # 初始化角色
    print("\nInitializing roles...")
    Role.insert_roles()
    print("Roles initialized successfully!")
    
    # 初始化管理员用户
    print("\nInitializing admin user...")
    admin_role = Role.query.filter_by(name='Admin').first()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role=admin_role)
        admin.password = 'admin123'
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: admin/admin123")
    else:
        print("Admin user already exists")