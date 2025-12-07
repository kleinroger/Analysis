from flask import request, current_app
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from app import socketio, db
from app.models import ChatMessage, User, AIEngine
from app.chat.ai_utils import call_ai_api, get_manbo_prompt, get_random_music, get_weather
import time
import re

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        # Join a personal room for private messages
        join_room(f"user_{current_user.id}")
        # Join global room
        join_room("global")
        # emit('status', {'msg': f'{current_user.username} 上线了'}, room='global')

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        # emit('status', {'msg': f'{current_user.username} 下线了'}, room='global')
        pass

def handle_weather_request(app, user_content, user_id):
    """
    处理天气查询请求
    """
    with app.app_context():
        # 获取曼波用户
        manbo_user = User.query.filter_by(username='曼波').first()
        if not manbo_user:
            return
        
        # 从用户消息中提取城市名称
        city = user_content
        city = re.sub(r'@曼波\s*', '', city)
        remove_words = ['天气', '查询天气', '天气预报', '查天气', '的天气', '天气怎么样', '怎么样']
        for word in remove_words:
            city = city.replace(word, '')
        city = city.strip()
        
        # 如果没有提取到城市，使用默认城市
        if not city:
            city = '北京'
        
        # 调用天气 API
        weather_data = get_weather(city)
        
        if weather_data:
            # 保存天气消息到数据库
            weather_content = json.dumps(weather_data, ensure_ascii=False)
            weather_msg = ChatMessage(
                sender_id=manbo_user.id,
                receiver_id=None,
                content=weather_content,
                msg_type='weather'
            )
            db.session.add(weather_msg)
            db.session.commit()
            
            # 发送天气卡片到前端
            socketio.emit('new_message', {
                'id': weather_msg.id,
                'sender_id': manbo_user.id,
                'sender_name': manbo_user.username,
                'receiver_id': None,
                'content': weather_content,
                'msg_type': 'weather',
                'created_at': weather_msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if weather_msg.created_at else ''
            }, room='global')
        else:
            # 发送错误消息
            error_msg = ChatMessage(
                sender_id=manbo_user.id,
                receiver_id=None,
                content=f'抱歉，无法获取 {city} 的天气信息，请检查城市名称是否正确~',
                msg_type='text'
            )
            db.session.add(error_msg)
            db.session.commit()
            
            socketio.emit('new_message', error_msg.to_dict(), room='global')

def handle_movie_request(app, user_content, user_id):
    """
    处理电影/视频播放请求
    """
    with app.app_context():
        # 获取曼波用户
        manbo_user = User.query.filter_by(username='曼波').first()
        if not manbo_user:
            return
        
        # 从用户消息中提取视频 URL
        # 支持常见视频网站链接
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, user_content)
        
        if urls:
            video_url = urls[0]  # 取第一个 URL
            # 解析服务器地址
            parser_base = "https://jx.m3u8.tv/jiexi/?url="
            iframe_src = parser_base + video_url
            
            # 构建电影数据
            movie_data = {
                'url': video_url,
                'iframe_src': iframe_src
            }
            
            # 保存电影消息到数据库
            movie_content = json.dumps(movie_data, ensure_ascii=False)
            movie_msg = ChatMessage(
                sender_id=manbo_user.id,
                receiver_id=None,
                content=movie_content,
                msg_type='movie'
            )
            db.session.add(movie_msg)
            db.session.commit()
            
            # 发送电影卡片到前端
            socketio.emit('new_message', {
                'id': movie_msg.id,
                'sender_id': manbo_user.id,
                'sender_name': manbo_user.username,
                'receiver_id': None,
                'content': movie_content,
                'msg_type': 'movie',
                'created_at': movie_msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if movie_msg.created_at else ''
            }, room='global')
        else:
            # 没有找到 URL，发送提示消息
            error_msg = ChatMessage(
                sender_id=manbo_user.id,
                receiver_id=None,
                content='请提供视频链接哦~ 例如：@曼波 电影 https://v.qq.com/x/cover/xxx.html',
                msg_type='text'
            )
            db.session.add(error_msg)
            db.session.commit()
            
            socketio.emit('new_message', error_msg.to_dict(), room='global')

def handle_music_request(app, user_content, user_id):
    """
    处理音乐播放请求
    """
    with app.app_context():
        # 获取曼波用户
        manbo_user = User.query.filter_by(username='曼波').first()
        if not manbo_user:
            return
        
        # 从用户消息中提取搜索关键词
        # 移除 @曼波 和常见的指令词，剩下的作为搜索关键词
        keyword = user_content
        keyword = re.sub(r'@曼波\s*', '', keyword)
        remove_words = ['播放音乐', '放首歌', '来首歌', '听歌', '放歌', '音乐', '播放', '我想听', '给我放', '来一首']
        for word in remove_words:
            keyword = keyword.replace(word, '')
        keyword = keyword.strip()
        
        # 如果没有提取到关键词，使用默认关键词
        if not keyword:
            keyword = '热门歌曲'
        
        # 调用音乐 API
        music_data = get_random_music(keyword)
        
        if music_data:
            # 保存音乐消息到数据库
            music_content = json.dumps(music_data, ensure_ascii=False)
            music_msg = ChatMessage(
                sender_id=manbo_user.id,
                receiver_id=None,
                content=music_content,
                msg_type='music'
            )
            db.session.add(music_msg)
            db.session.commit()
            
            # 发送音乐卡片到前端
            socketio.emit('new_message', {
                'id': music_msg.id,
                'sender_id': manbo_user.id,
                'sender_name': manbo_user.username,
                'receiver_id': None,
                'content': music_content,
                'msg_type': 'music',
                'created_at': music_msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if music_msg.created_at else ''
            }, room='global')
        else:
            # 发送错误消息
            error_msg = ChatMessage(
                sender_id=manbo_user.id,
                receiver_id=None,
                content='抱歉，暂时无法获取音乐，请稍后再试~',
                msg_type='text'
            )
            db.session.add(error_msg)
            db.session.commit()
            
            socketio.emit('new_message', error_msg.to_dict(), room='global')

# 需要导入 json
import json

def handle_ai_response(app, user_content, user_name, user_id):
    """
    后台任务处理 AI 响应
    """
    with app.app_context(): # 需要应用上下文来访问数据库
        # 1. 获取 AI 配置
        engine = AIEngine.query.filter_by(provider_name='SiliconFlow', is_active=True).first()
        if not engine:
            return

        # 2. 获取曼波用户
        manbo_user = User.query.filter_by(username='曼波').first()
        if not manbo_user:
            return

        # 3. 准备 Prompt
        system_prompt = get_manbo_prompt()
        # 注入当前用户信息到 System Prompt 或者作为 User Context
        # 根据需求：如果是杰哥和你对话，你会有额外的欢迎词
        if user_name == '杰哥':
            system_prompt += "\n当前对话的用户是：杰哥。"
        else:
            system_prompt += f"\n当前对话的用户是：{user_name}。"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        # 4. 生成一个临时的消息 ID (前端用)
        temp_msg_id = f"ai_{int(time.time() * 1000)}"
        
        # 5. 通知前端 AI 开始思考/输入
        socketio.emit('ai_typing_start', {
            'sender_id': manbo_user.id,
            'sender_name': manbo_user.username,
            'temp_id': temp_msg_id
        }, room='global')

        full_response = ""
        
        # 6. 调用 API 并流式输出
        for chunk in call_ai_api(messages, engine.api_key, engine.api_url, engine.model_name):
            full_response += chunk
            socketio.emit('ai_message_chunk', {
                'temp_id': temp_msg_id,
                'chunk': chunk,
                'sender_id': manbo_user.id,
                'sender_name': manbo_user.username
            }, room='global')
            time.sleep(0.02) # 稍微延迟一下，避免前端刷新太快

        # 7. 保存完整消息到数据库
        ai_msg = ChatMessage(
            sender_id=manbo_user.id,
            receiver_id=None, # 群聊
            content=full_response,
            msg_type='text'
        )
        db.session.add(ai_msg)
        db.session.commit()
        
        # 8. 通知前端消息结束（可选，确认最终状态）
        socketio.emit('ai_message_end', {
            'temp_id': temp_msg_id,
            'final_id': ai_msg.id,
            'content': full_response
        }, room='global')

@socketio.on('send_message')
def handle_message(data):
    # data: {content, receiver_id (optional), msg_type, file_url, file_name, file_size}
    content = data.get('content')
    receiver_id = data.get('receiver_id')
    msg_type = data.get('msg_type', 'text')  # text, image, file
    
    if not content:
        return

    msg = ChatMessage(
        sender_id=current_user.id,
        receiver_id=receiver_id if receiver_id else None,
        content=content,
        msg_type=msg_type
    )
    db.session.add(msg)
    db.session.commit()
    
    payload = msg.to_dict()
    # 附加文件信息到 payload
    if msg_type in ('image', 'file'):
        payload['file_name'] = data.get('file_name', '')
        payload['file_size'] = data.get('file_size', 0)
    
    if receiver_id:
        # Private: Emit to sender and receiver
        emit('new_message', payload, room=f"user_{receiver_id}")
        emit('new_message', payload, room=f"user_{current_user.id}") # Echo back
    else:
        # Group: Emit to global
        emit('new_message', payload, room='global')
        
        # 检查是否触发 @曼波 (仅在群聊且为文本消息时)
        if msg_type == 'text' and '@曼波' in content:
            app_obj = current_app._get_current_object()
            
            # 检测天气查询指令
            weather_keywords = ['天气', '天气预报', '查天气']
            is_weather_request = any(keyword in content for keyword in weather_keywords)
            
            # 检测电影播放指令
            movie_keywords = ['电影', '视频', '播放视频', '看电影', '看视频']
            is_movie_request = any(keyword in content for keyword in movie_keywords)
            
            # 检测音乐播放指令
            music_keywords = ['播放音乐', '放首歌', '来首歌', '听歌', '放歌', '音乐']
            is_music_request = any(keyword in content for keyword in music_keywords)
            
            if is_weather_request:
                # 处理天气请求
                socketio.start_background_task(handle_weather_request, app_obj, content, current_user.id)
            elif is_movie_request:
                # 处理电影请求
                socketio.start_background_task(handle_movie_request, app_obj, content, current_user.id)
            elif is_music_request:
                # 处理音乐请求
                socketio.start_background_task(handle_music_request, app_obj, content, current_user.id)
            else:
                # 处理普通 AI 对话
                socketio.start_background_task(handle_ai_response, app_obj, content, current_user.username, current_user.id)

