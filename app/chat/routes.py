import os
import uuid
from datetime import datetime
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from . import bp
from app.models import User, ChatMessage
from app import db

# 允许的文件类型
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
ALLOWED_FILE_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip', 'rar', '7z', 'mp3', 'mp4', 'avi', 'mov'}

def allowed_file(filename, file_type='image'):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if file_type == 'image':
        return ext in ALLOWED_IMAGE_EXTENSIONS
    else:
        return ext in (ALLOWED_IMAGE_EXTENSIONS | ALLOWED_FILE_EXTENSIONS)

def get_upload_folder():
    """获取上传目录，按日期分类"""
    base_path = os.path.join(current_app.root_path, '..', 'static', 'uploads', 'chat')
    date_folder = datetime.now().strftime('%Y%m')
    upload_path = os.path.join(base_path, date_folder)
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)
    return upload_path, date_folder

@bp.route('/')
@login_required
def index():
    # Get all users for contact list (excluding self)
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('chat/index.html', users=users)

@bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """处理文件上传"""
    if 'file' not in request.files:
        return jsonify({'code': 1, 'msg': '没有选择文件'})
    
    file = request.files['file']
    file_type = request.form.get('type', 'file')  # 'image' or 'file'
    
    if file.filename == '':
        return jsonify({'code': 1, 'msg': '没有选择文件'})
    
    if not allowed_file(file.filename, file_type):
        return jsonify({'code': 1, 'msg': '不支持的文件类型'})
    
    # 检查文件大小 (最大 20MB)
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > 20 * 1024 * 1024:
        return jsonify({'code': 1, 'msg': '文件大小不能超过 20MB'})
    
    # 生成安全的文件名 - 直接从原始文件名获取扩展名
    original_filename = file.filename
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    if not ext:
        # 如果没有扩展名，尝试从 MIME 类型推断
        mime_to_ext = {
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'image/bmp': 'bmp'
        }
        ext = mime_to_ext.get(file.content_type, 'bin')
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    
    # 保存文件
    upload_path, date_folder = get_upload_folder()
    file_path = os.path.join(upload_path, unique_filename)
    file.save(file_path)
    
    # 返回文件 URL
    file_url = f"/static/uploads/chat/{date_folder}/{unique_filename}"
    
    return jsonify({
        'code': 0,
        'msg': '上传成功',
        'data': {
            'url': file_url,
            'filename': file.filename,  # 原始文件名
            'size': file_size,
            'type': file_type
        }
    })

@bp.route('/history')
@login_required
def history():
    target_id = request.args.get('target_id', type=int)
    # If target_id is None or 0, it is group chat
    if not target_id:
        msgs = ChatMessage.query.filter_by(receiver_id=None)\
            .order_by(ChatMessage.created_at.desc()).limit(50).all()
    else:
        # Private chat: (sender=me and receiver=target) OR (sender=target and receiver=me)
        msgs = ChatMessage.query.filter(
            ((ChatMessage.sender_id == current_user.id) & (ChatMessage.receiver_id == target_id)) |
            ((ChatMessage.sender_id == target_id) & (ChatMessage.receiver_id == current_user.id))
        ).order_by(ChatMessage.created_at.desc()).limit(50).all()
    
    # Reverse to show chronological
    data = [m.to_dict() for m in msgs][::-1]
    return jsonify({'code': 0, 'data': data})
