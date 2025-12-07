from flask import Blueprint, render_template, request, jsonify
from app.crawler import BaiduCrawler

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/api/crawl')
def api_crawl():
    q = request.args.get('q', '').strip()
    src = (request.args.get('src', 'baidu') or 'baidu').lower()
    limit_arg = request.args.get('limit', '30')
    pages_arg = request.args.get('max_pages', '5')
    try:
        limit = int(limit_arg)
    except Exception:
        limit = 30
    try:
        max_pages = int(pages_arg)
    except Exception:
        max_pages = 5
    if limit <= 0:
        limit = 1
    if max_pages <= 0:
        max_pages = 1
    crawler = BaiduCrawler() if src == 'baidu' else None
    if src == 'xinhua':
        from app.crawler import XinhuaCrawler
        crawler = XinhuaCrawler()
    data = crawler.crawl(q, limit=limit, max_pages=max_pages) if crawler else []
    def _normalize(item):
        return {
            "title": item.get("title") or item.get("标题") or "",
            "summary": item.get("summary") or item.get("概要") or "",
            "cover": item.get("cover") or item.get("封面") or "",
            "url": item.get("url") or item.get("原始URL") or "",
            "source": item.get("source") or item.get("来源") or ""
        }
    def _is_dirty(item):
        c = 0
        if not item.get("url"):
            c += 1
        if not item.get("cover"):
            c += 1
        src = item.get("source", "")
        if not src:
            c += 1
        title = item.get("title", "")
        if not title:
            c += 1
        if not item.get("summary"):
            c += 1
        return c >= 3
    normalized = []
    for i in data:
        n = _normalize(i)
        if not _is_dirty(n):
            normalized.append(n)
    return jsonify(normalized)
