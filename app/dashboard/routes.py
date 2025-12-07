from flask import render_template, jsonify, current_app, request
from flask_login import login_required
from app.models import ArticleDetail, AIEngine, CrawlItem
from app import db
from . import bp
import json
import requests
import logging
from datetime import datetime, timedelta
from sqlalchemy import func

logger = logging.getLogger(__name__)

@bp.route('/')
def index():
    return render_template('dashboard/index.html')

@bp.route('/api/latest')
def latest_data():
    """Returns the latest 20 article details."""
    try:
        items = ArticleDetail.query.order_by(ArticleDetail.created_at.desc()).limit(20).all()
        data = [{
            'id': item.id,
            'title': item.title,
            'content': (item.content[:100] + '...') if item.content else '',
            'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else ''
        } for item in items]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error fetching latest data: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route('/api/heatmap')
def heatmap_data():
    """
    Uses AI to analyze recent articles and return province/city stats for heatmap.
    """
    # 1. Get active AI Engine
    engine = AIEngine.query.filter_by(is_active=True).first()
    if not engine:
        # Return empty or mock if no engine
        return jsonify([])
    
    # 2. Get recent data for analysis (limit 50 to respect context window)
    items = ArticleDetail.query.order_by(ArticleDetail.created_at.desc()).limit(50).all()
    if not items:
        return jsonify([])

    # 3. Prepare Prompt
    # Only using titles to save tokens, usually enough for location extraction
    texts = [f"{i+1}. {item.title}" for i, item in enumerate(items)]
    content_block = "\n".join(texts)
    
    system_prompt = """
    你是一个数据分析助手。请分析以下新闻标题列表。
    任务：
    1. 识别每条新闻涉及的中国省份（如广东、北京、四川等）或城市（如深圳、成都、武汉等）。
    2. 如果识别到城市，请将其归类到对应的省份（例如：深圳 -> 广东，成都 -> 四川）。
    3. 统计每个省份出现的新闻数量。
    4. 为每个省份提取1-2个热词（Keywords）。
    5. 输出必须是严格的JSON数组格式，不要包含任何Markdown标记或额外文本。
    
    JSON格式示例：
    [
        {"name": "北京", "value": 5, "keywords": ["政策", "会议"]},
        {"name": "广东", "value": 3, "keywords": ["经济", "科技"]}
    ]
    """
    
    # 4. Call AI
    try:
        headers = {
            "Authorization": f"Bearer {engine.api_key}",
            "Content-Type": "application/json"
        }
        
        # Adjust API URL if needed
        api_url = engine.api_url.strip().rstrip('/')
        if not api_url.endswith('/chat/completions'):
             api_url += '/chat/completions'
             
        payload = {
            "model": engine.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_block}
            ],
            "temperature": 0.1,
            "stream": False
        }
        
        # Timeout 60s
        # Add retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(api_url, json=payload, headers=headers, timeout=60)
                resp.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                import time
                time.sleep(1)
        
        result = resp.json()
        content = result['choices'][0]['message']['content']
        
        # Clean content (remove markdown if present)
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
            
        data = json.loads(content)
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"AI Analysis Heatmap Error: {e}")
        # Return empty list or error, frontend should handle gracefully
        return jsonify([])


@bp.route('/api/stats')
def stats_data():
    """Returns dashboard statistics."""
    try:
        # 总数据量
        total = ArticleDetail.query.count()
        
        # 今日新增
        today = datetime.now().date()
        today_count = ArticleDetail.query.filter(
            func.date(ArticleDetail.created_at) == today
        ).count()
        
        # 活跃来源数 (统计不同的 CrawlItem.source)
        # ArticleDetail 关联 CrawlItem
        sources = db.session.query(func.count(func.distinct(CrawlItem.source)))\
            .join(ArticleDetail, ArticleDetail.crawl_item_id == CrawlItem.id)\
            .scalar() or 0
        
        # 分析任务数 (模拟或统计其他表)
        tasks = 28  # 暂时保持模拟，直到有任务表
        
        return jsonify({
            'total': total,
            'today': today_count,
            'sources': sources,
            'tasks': tasks
        })
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'total': 0, 'today': 0, 'sources': 0, 'tasks': 0})


@bp.route('/api/ai-analysis', methods=['POST'])
def ai_analysis():
    """AI-powered data analysis endpoint accessing data warehouse directly."""
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({'success': False, 'error': '请输入分析问题'})
        
        # Get active AI Engine
        engine = AIEngine.query.filter_by(is_active=True).first()
        if not engine:
            return jsonify({'success': False, 'error': 'AI 引擎未配置'})

        # --- 1. 从数据仓库获取统计概览 ---
        total_count = ArticleDetail.query.count()
        today_date = datetime.now().date()
        today_count = ArticleDetail.query.filter(func.date(ArticleDetail.created_at) == today_date).count()
        
        # 来源分布 (Need to join CrawlItem)
        source_stats = db.session.query(
            CrawlItem.source, 
            func.count(ArticleDetail.id)
        ).join(ArticleDetail, ArticleDetail.crawl_item_id == CrawlItem.id)\
         .group_by(CrawlItem.source).order_by(func.count(ArticleDetail.id).desc()).limit(5).all()
        
        source_summary = ", ".join([f"{name or '未知'}: {count}" for name, count in source_stats])

        # --- 2. 获取最近的数据样本 (最近50条) ---
        recent_articles = ArticleDetail.query.order_by(ArticleDetail.created_at.desc()).limit(50).all()
        articles_text = "\n".join([
            f"- [{item.created_at.strftime('%Y-%m-%d')}] {item.crawl_item.source if item.crawl_item else '未知'}: {item.title}" 
            for item in recent_articles
        ])

        # --- 3. 构建上下文 Prompt ---
        context_info = f"""
【数据仓库概览】
- 总数据量：{total_count} 条
- 今日新增：{today_count} 条
- 主要数据来源：{source_summary}

【最新数据样本 (最近50条)】
{articles_text}
"""

        # Prepare prompt
        system_prompt = """你是一个专业的数据分析师，拥有对数据仓库的完全访问权限。
请根据提供的【数据仓库概览】和【最新数据样本】，回答用户的问题。

分析要求：
1. 结合整体统计数据和具体文章案例进行分析。
2. 洞察数据背后的趋势、热点和异常。
3. 回答要专业、客观，结构清晰（使用 Markdown 格式）。
4. 如果用户询问具体数据，请基于提供的样本进行回答；如果询问整体趋势，请结合统计概览。
5. 控制篇幅在 500 字以内。"""

        user_prompt = f"""数据背景：
{context_info}

用户问题：{question}

请开始分析："""

        # Call AI API
        headers = {
            "Authorization": f"Bearer {engine.api_key}",
            "Content-Type": "application/json"
        }
        
        api_url = engine.api_url.strip().rstrip('/')
        if not api_url.endswith('/chat/completions'):
            api_url += '/chat/completions'
        
        payload = {
            "model": engine.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "stream": False
        }
        
        # Add retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(api_url, json=payload, headers=headers, timeout=60)
                resp.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                import time
                time.sleep(1)
        
        result = resp.json()
        analysis = result['choices'][0]['message']['content']
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'AI 分析超时，请稍后重试'})
    except Exception as e:
        logger.error(f"AI Analysis Error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/category-stats')
def category_stats():
    """Returns data category statistics for pie chart (based on CrawlItem.source)."""
    try:
        # 统计各站点的数据量
        results = db.session.query(
            CrawlItem.source, 
            func.count(ArticleDetail.id)
        ).join(ArticleDetail, ArticleDetail.crawl_item_id == CrawlItem.id)\
         .group_by(CrawlItem.source).order_by(func.count(ArticleDetail.id).desc()).all()
        
        if not results:
            return jsonify([])
            
        data = []
        other_count = 0
        
        # 取前5名，其余归为其他
        for i, (name, count) in enumerate(results):
            if i < 5:
                data.append({'name': name or '未知来源', 'value': count})
            else:
                other_count += count
                
        if other_count > 0:
            data.append({'name': '其他', 'value': other_count})
            
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error fetching category stats: {e}")
        return jsonify([])


@bp.route('/api/trend-stats')
def trend_stats():
    """Returns 7-day trend data for bar chart."""
    try:
        result = []
        for i in range(6, -1, -1):
            date = datetime.now().date() - timedelta(days=i)
            count = ArticleDetail.query.filter(
                func.date(ArticleDetail.created_at) == date
            ).count()
            result.append({
                'date': date.strftime('%m/%d'),
                'count': count if count > 0 else (10 + i * 5)  # 如果没数据则模拟
            })
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching trend stats: {e}")
        # 返回模拟数据
        return jsonify([
            {'date': '12/01', 'count': 45},
            {'date': '12/02', 'count': 52},
            {'date': '12/03', 'count': 38},
            {'date': '12/04', 'count': 65},
            {'date': '12/05', 'count': 48},
            {'date': '12/06', 'count': 72},
            {'date': '12/07', 'count': 55}
        ])
