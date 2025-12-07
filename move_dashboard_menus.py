from app import create_app, db
from app.models import Menu

app = create_app()
with app.app_context():
    # Get menus to move
    menus_to_move = ['首页概览', '数据大屏']
    
    for name in menus_to_move:
        menu = Menu.query.filter_by(name=name).first()
        if menu:
            menu.parent_id = None
            print(f"Moved '{name}' to top level.")
        else:
            print(f"Menu '{name}' not found.")
            
    # Check '工作台'
    workbench = Menu.query.filter_by(name='工作台').first()
    if workbench:
        # Check if it has any children left
        children_count = Menu.query.filter_by(parent_id=workbench.id).count()
        if children_count == 0:
            db.session.delete(workbench)
            print("Deleted empty '工作台' menu.")
        else:
            print(f"'工作台' still has {children_count} children.")
            
    db.session.commit()
    print("Menu structure updated successfully.")
