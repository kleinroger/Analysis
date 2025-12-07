import os
from app import create_app, db
from app.models import User, Role

app = create_app()

with app.app_context():
    # Init Roles
    Role.insert_roles()
    
    # Init Admin User if not exists
    admin_role = Role.query.filter_by(name='Admin').first()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role=admin_role)
        admin.password = 'admin123'
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: admin/admin123")
    else:
        print("Admin user already exists")