import requests
import time
import json

# API 基础 URL
BASE_URL = 'http://127.0.0.1:5000/collect/api'
LOGIN_URL = 'http://127.0.0.1:5000/auth/login'

print("测试前端交互流程...")
print("=" * 50)

# 创建会话
session = requests.Session()

# 0. 先登录
print("0. 登录系统...")
login_data = {
    "username": "admin",  # 默认管理员用户名
    "password": "admin123"   # 默认管理员密码
}

login_response = session.post(LOGIN_URL, data=login_data, allow_redirects=False)
if login_response.status_code != 302:  # 登录成功应该重定向
    print(f"登录失败: {login_response.status_code} - {login_response.text}")
    exit(1)

print("登录成功!")

# 1. 启动采集任务
print("1. 启动采集任务...")
start_data = {
    "q": "西昌",  # 使用前端的参数名
    "limit": 5,
    "max_pages": 1,  # 使用前端的参数名
    "src": "baidu"  # 使用前端的参数名
}

start_response = session.post(f'{BASE_URL}/start', json=start_data)
print(f"响应状态码: {start_response.status_code}")
print(f"响应头: {start_response.headers}")
print(f"响应内容: {start_response.text}")

if start_response.status_code != 200:
    print(f"启动任务失败: {start_response.status_code} - {start_response.text}")
    exit(1)

try:
    start_result = start_response.json()
    print(f"启动成功! 任务ID: {start_result.get('job_id')}")
    job_id = start_result.get('job_id')
except Exception as e:
    print(f"解析JSON失败: {e}")
    exit(1)

# 2. 轮询状态
print("\n2. 轮询任务状态...")
max_polls = 20
for i in range(max_polls):
    status_response = session.get(f'{BASE_URL}/status', params={'job_id': job_id})
    if status_response.status_code != 200:
        print(f"获取状态失败: {status_response.status_code} - {status_response.text}")
        break
    
    status = status_response.json()
    print(f"  状态: {status.get('state')}, 进度: {status.get('progress')}%, 文本: {status.get('status_text')}")
    
    if status.get('state') in ['completed', 'error']:
        break
    
    time.sleep(1)  # 等待1秒再轮询
else:
    print("\n轮询超时!")

# 3. 检查结果
print("\n3. 检查采集结果...")
status_response = session.get(f'{BASE_URL}/status', params={'job_id': job_id})
if status_response.status_code == 200:
    final_status = status_response.json()
    items = final_status.get('items', [])
    print(f"  采集到 {len(items)} 条结果")
    
    if items:
        print("\n  前3条结果:")
        for i, item in enumerate(items[:3], 1):
            print(f"  {i}. 标题: {item.get('title', 'N/A')}")
            print(f"     URL: {item.get('url', 'N/A')}")
            print(f"     来源: {item.get('source', 'N/A')}")
            print(f"     发布时间: {item.get('published_at', 'N/A')}")
            print()
    else:
        print("  没有采集到任何结果!")
        if final_status.get('error'):
            print(f"  错误信息: {final_status.get('error')}")

print("\n" + "=" * 50)
print("测试完成!")
