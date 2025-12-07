from app import create_app, db
from app.models import User, Role, AIEngine

app = create_app()

with app.app_context():
    # 1. 确保“曼波”用户存在
    manbo = User.query.filter_by(username='曼波').first()
    if not manbo:
        # 获取 User 角色
        user_role = Role.query.filter_by(name='User').first()
        if not user_role:
            print("Error: User role not found. Please run init db first.")
        else:
            manbo = User(username='曼波', role=user_role)
            manbo.password = 'manbo123' # 设置一个默认密码
            db.session.add(manbo)
            db.session.commit()
            print("User '曼波' created.")
    else:
        print("User '曼波' already exists.")

    # 2. 配置 AI 引擎
    # 检查是否已存在 SiliconFlow 配置，如果存在则更新，不存在则创建
    # 注意：这里我们简单地查找 provider_name 为 'SiliconFlow' 的记录
    engine = AIEngine.query.filter_by(provider_name='SiliconFlow').first()
    
    api_key = "sk-kdvhthauwimhtxwtjomlfopfjxekxfwkdzaknhmumtfmhfsn"
    model_name = "Qwen/Qwen2.5-7B-Instruct"
    api_url = "https://api.siliconflow.cn/v1/"
    
    if engine:
        engine.api_key = api_key
        engine.model_name = model_name
        engine.api_url = api_url
        engine.is_active = True
        print("Updated SiliconFlow AI Engine config.")
    else:
        engine = AIEngine(
            provider_name='SiliconFlow',
            api_url=api_url,
            api_key=api_key,
            model_name=model_name,
            is_active=True
        )
        db.session.add(engine)
        print("Created SiliconFlow AI Engine config.")
    
    db.session.commit()
