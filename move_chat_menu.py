from app import create_app, db
from app.models import Menu

app = create_app()
with app.app_context():
    # 获取聊天室菜单
    chat_menu = Menu.query.filter_by(name='聊天室').first()
    
    if chat_menu:
        # 设置 parent_id 为 None，使其成为一级菜单
        chat_menu.parent_id = None
        # 可选：调整顺序，使其排在系统管理之前或之后，这里暂时不改 order
        
        db.session.commit()
        print(f"Moved '聊天室' to top level (Parent ID set to None)")
    else:
        print("Menu '聊天室' not found.")
        
    print("Menu structure updated successfully.")
