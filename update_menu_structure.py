from app import create_app, db
from app.models import Menu

app = create_app()
with app.app_context():
    # 1. 将“数据仓库”移动到“采集与处理”之下
    warehouse_menu = Menu.query.filter_by(name='数据仓库').first()
    collect_parent = Menu.query.filter_by(name='采集与处理').first()
    
    if warehouse_menu and collect_parent:
        warehouse_menu.parent_id = collect_parent.id
        print(f"Moved '数据仓库' to '采集与处理' (Parent ID: {collect_parent.id})")

    # 2. 添加“报告管理”菜单到“采集与处理”之下
    report_menu = Menu.query.filter_by(url='reports.index').first()
    if not report_menu and collect_parent:
        report_menu = Menu(
            name='报告管理',
            icon='layui-icon-file-text',
            url='reports.index',
            parent_id=collect_parent.id,
            order=5,
            is_visible=True
        )
        db.session.add(report_menu)
        print("Added '报告管理' menu")
    elif report_menu and collect_parent:
        report_menu.parent_id = collect_parent.id
        print("Updated '报告管理' parent")

    # 3. 删除空的“数据中心”菜单
    data_center = Menu.query.filter_by(name='数据中心').first()
    if data_center:
        # Check if it has children
        children = Menu.query.filter_by(parent_id=data_center.id).count()
        if children == 0:
            db.session.delete(data_center)
            print("Deleted empty '数据中心' menu")
        else:
            print(f"'数据中心' still has {children} children, skipping delete")

    db.session.commit()
    print("Menu structure updated successfully.")
