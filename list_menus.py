from app import create_app, db
from app.models import Menu

app = create_app()
with app.app_context():
    menus = Menu.query.all()
    print(f"{'ID':<5} {'Name':<20} {'ParentID':<10} {'URL'}")
    print("-" * 50)
    for m in menus:
        print(f"{m.id:<5} {m.name:<20} {str(m.parent_id):<10} {m.url}")
