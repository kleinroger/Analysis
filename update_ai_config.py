from app import create_app, db
from app.models import AIEngine

app = create_app()
with app.app_context():
    # 查找当前活跃的 AI 引擎
    engine = AIEngine.query.filter_by(is_active=True).first()
    
    if not engine:
        # 如果没有活跃引擎，创建一个新的
        print("No active AI Engine found. Creating a new one...")
        engine = AIEngine(is_active=True, provider_name='SiliconFlow')
        db.session.add(engine)
    
    # 更新配置
    engine.api_key = 'sk-jlmfiytyvppjvpqqziiezflxlehtmqthoziyascvjlswteql'
    engine.model_name = 'Qwen/Qwen3-8B'
    engine.api_url = 'https://api.siliconflow.cn'
    engine.provider_name = 'SiliconFlow' # 确保提供商名称也更新
    
    db.session.commit()
    print("AI Engine configuration updated successfully:")
    print(f"Provider: {engine.provider_name}")
    print(f"API URL: {engine.api_url}")
    print(f"Model: {engine.model_name}")
    print(f"API Key: {engine.api_key[:10]}...{engine.api_key[-5:]}")
