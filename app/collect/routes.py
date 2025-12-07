import uuid
import threading
import time
import random
import logging
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import CrawlItem, CrawlSource
from app.crawler import BaiduCrawler, XinhuaCrawler, ChinaSoCrawler, DynamicCrawler, SinaCrawler
from bs4 import BeautifulSoup
from . import bp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread-safe job store
job_store = {}
job_store_lock = threading.Lock()

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            return jsonify({"error": "forbidden"}), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
def index():
    return render_template('collect/index.html')

def _run_job(job_id, keyword, limit, max_pages, src):
    from app import create_app
    
    # Create a new application instance for this thread
    app = create_app()
    
    with app.app_context():
        from app.models import CrawlSource
        
        logger.info(f"Starting job {job_id} with application context")
        
        with job_store_lock:
            job = job_store.get(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return

        try:
            logger.info(f"Starting job {job_id} for keyword '{keyword}'")
            # Determine crawler strategy
            # Priority: Built-in Classes > Dynamic Configuration
            
            # Map Chinese names or IDs to built-in logic
            if src in ['baidu', '百度新闻', '百度']:
                crawler = BaiduCrawler()
            elif src in ['sina', '新浪新闻', '新浪']:
                crawler = SinaCrawler()
            elif src in ['xinhua', '新华网', '新华']:
                crawler = XinhuaCrawler()
            elif src in ['chinaso', '中国搜索', '国搜']:
                crawler = ChinaSoCrawler()
            else:
                # Try dynamic source from DB
                dynamic = CrawlSource.query.filter_by(name=src, is_active=True).first()
                if dynamic:
                    config = {
                        "base_url": dynamic.base_url,
                        "headers": json.loads(dynamic.headers) if dynamic.headers else {},
                        "params": json.loads(dynamic.params) if dynamic.params else {},
                        "pagination": json.loads(dynamic.pagination) if dynamic.pagination else {},
                        "selectors": json.loads(dynamic.selectors) if dynamic.selectors else {}
                    }
                    crawler = DynamicCrawler(config)
                else:
                    # Fallback default
                    crawler = XinhuaCrawler()
            
            items = []
            
            # Update job status
            with job_store_lock:
                job["status_text"] = "正在初始化爬虫..."
            
            logger.info(f"Crawler initialized for job {job_id}")
            
            # 使用爬虫的crawl方法直接采集数据
            if src == 'xinhua' and not keyword:
                # 新华网爬虫不需要关键词
                results = crawler.crawl('', limit=limit, max_pages=max_pages)
            else:
                results = crawler.crawl(keyword, limit=limit, max_pages=max_pages)
            
            logger.info(f"Crawl completed for job {job_id}, got {len(results)} results")
            
            # 更新进度和状态
            with job_store_lock:
                job["status_text"] = "正在处理采集结果..."
                job["progress"] = 50
            
            # 处理结果
            seen = set()
            for it in results:
                key = it.get("url") or (it.get("title", "") + it.get("source", ""))
                if key in seen:
                    continue
                seen.add(key)
                # 移除严格的关键词过滤
                items.append(it)
                
                # Update job with new items and progress
                with job_store_lock:
                    job["items"] = items.copy()  # Use copy for thread safety
                    job["progress"] = 50 + min(49, int((len(items) / max(1, limit)) * 50))
                
                if len(items) >= limit:
                    break
            
            logger.info(f"Result processing completed for job {job_id}, final items: {len(items)}")
            
            # Update job to completed
            with job_store_lock:
                job["progress"] = 100
                job["state"] = "completed"
                job["status_text"] = "采集完成"
        except Exception as e:
            logger.error(f"Error in job {job_id}: {str(e)}", exc_info=True)
            with job_store_lock:
                job["state"] = "error"
                job["error"] = str(e)
                job["status_text"] = f"出错: {str(e)}"

@bp.route('/api/start', methods=['POST'])
@login_required
def api_start():
    data = request.get_json(force=True) or {}
    keyword = str(data.get('keyword') or data.get('q', '')).strip()
    limit = int(data.get('limit', 30))
    max_pages = int(data.get('max_pages', 5))
    src = (data.get('src') or 'baidu').lower()
    if src == 'baidu' and not keyword:
        return jsonify({"error": "keyword required"}), 400
    job_id = uuid.uuid4().hex
    job_store[job_id] = {"state": "running", "progress": 0, "items": [], "src": src, "keyword": keyword}
    t = threading.Thread(target=_run_job, args=(job_id, keyword, limit, max_pages, src), daemon=True)
    t.start()
    return jsonify({"job_id": job_id})

@bp.route('/api/status')
@login_required
def api_status():
    job_id = request.args.get('job_id', '')
    job = job_store.get(job_id)
    if not job:
        return jsonify({"error": "not_found"}), 404
    return jsonify(job)

@bp.route('/api/deep', methods=['POST'])
@login_required
@admin_required
def api_deep():
    return jsonify({"error": "deep_disabled"}), 403

@bp.route('/api/store', methods=['POST'])
@login_required
def api_store():
    data = request.get_json(force=True) or {}
    items = data.get('items') or []
    saved = 0
    updated = 0
    for it in items:
        url = it.get('url') or ''
        if not url:
            continue
        
        # Check existing
        existing = CrawlItem.query.filter_by(url=url).first()
        
        if existing:
            # Update
            existing.keyword = it.get('keyword') or data.get('keyword') or existing.keyword
            existing.title = it.get('title') or existing.title
            existing.cover = it.get('cover') or existing.cover
            existing.source = it.get('source') or existing.source
            existing.deep_crawled = bool(it.get('deep')) or existing.deep_crawled
            existing.deep_cover = it.get('deep_cover') or it.get('cover') or existing.deep_cover
            existing.deep_summary = it.get('deep_summary') or existing.deep_summary
            updated += 1
        else:
            # Insert
            m = CrawlItem(
                keyword=it.get('keyword') or data.get('keyword') or '',
                title=it.get('title') or '',
                cover=it.get('cover') or '',
                url=url,
                source=it.get('source') or '',
                deep_crawled=bool(it.get('deep')),
                deep_cover=it.get('deep_cover') or it.get('cover') or '',
                deep_summary=it.get('deep_summary') or ''
            )
            db.session.add(m)
            saved += 1
    db.session.commit()
    return jsonify({"saved": saved, "updated": updated})
