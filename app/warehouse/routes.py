from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import CrawlItem
from . import bp
from urllib.parse import urlparse

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
    return render_template('warehouse/index.html')

@bp.route('/api/list')
@login_required
def api_list():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword', '')
    
    query = CrawlItem.query.order_by(CrawlItem.created_at.desc())
    
    if keyword:
        query = query.filter(CrawlItem.title.contains(keyword) | CrawlItem.keyword.contains(keyword))
        
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    items = []
    
    # Optimization: Fetch bindings only for sources in current page
    from app.models import SourceBinding
    
    # 1. Collect sources from current page
    current_page_sources = set()
    for item in pagination.items:
        if item.source:
            current_page_sources.add(item.source)
            
    # 2. Fetch bindings for these sources
    binding_map = {}
    if current_page_sources:
        relevant_bindings = SourceBinding.query.filter(SourceBinding.source_name.in_(current_page_sources)).all()
        for b in relevant_bindings:
            key = (b.source_name, b.source_domain)
            if key not in binding_map:
                binding_map[key] = []
            if b.rule:
                binding_map[key].append(b.rule.site_name)
            
    for item in pagination.items:
        domain = ''
        if item.url:
            try:
                domain = urlparse(item.url).netloc
            except:
                pass
        has_detail = item.detail is not None
        
        # Check bindings
        bound_rules = binding_map.get((item.source, domain), [])
        
        items.append({
            "id": item.id,
            "keyword": item.keyword,
            "title": item.title,
            "source": item.source,
            "domain": domain, # Add domain to response
            "bound_rules": bound_rules, # Add bound rules
            "url": item.url,
            "created_at": item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '',
            "deep_summary": item.deep_summary,
            "deep_crawled": has_detail
        })
        
    return jsonify({
        "code": 0,
        "msg": "",
        "count": pagination.total,
        "data": items
    })

@bp.route('/api/stats')
@login_required
def api_stats():
    """获取数据仓库统计信息"""
    from sqlalchemy import func
    
    # 总数
    total = CrawlItem.query.count()
    
    # 已深采数量 (有 detail 的)
    from app.models import ArticleDetail
    crawled = db.session.query(func.count(ArticleDetail.id)).scalar() or 0
    
    # 来源数量
    sources = db.session.query(func.count(func.distinct(CrawlItem.source)))\
        .filter(CrawlItem.source != None, CrawlItem.source != "").scalar() or 0
    
    return jsonify({
        "code": 0,
        "data": {
            "total": total,
            "crawled": crawled,
            "sources": sources
        }
    })

@bp.route('/api/sources')
@login_required
@admin_required
def api_sources():
    keyword = request.args.get('keyword', '').strip()
    
    # Get all bindings for counting
    from app.models import SourceBinding
    all_bindings = SourceBinding.query.all()
    bound_counts = {} # (source_name, source_domain) -> count
    for b in all_bindings:
        key = (b.source_name, b.source_domain)
        bound_counts[key] = bound_counts.get(key, 0) + 1
        
    # Optimization: Query distinct source, url using GROUP BY
    from sqlalchemy import func
    query = db.session.query(CrawlItem.source, func.min(CrawlItem.url))\
        .filter(CrawlItem.source != None, CrawlItem.source != "")\
        .group_by(CrawlItem.source)
    
    if keyword:
        # Simple keyword filter on source or url
        query = query.filter(CrawlItem.source.contains(keyword) | CrawlItem.url.contains(keyword))
        
    results = query.all()
    
    source_map = {} # (source_name, domain) -> True
    
    for r in results:
        source = r[0]
        url = r[1]
        domain = ''
        if url:
            try:
                domain = urlparse(url).netloc
            except:
                pass
        key = (source, domain)
        source_map[key] = True
        
    # Convert to list
    data = []
    for (source, domain) in source_map.keys():
        count = bound_counts.get((source, domain), 0)
        data.append({
            "source": source,
            "domain": domain,
            "bound_count": count
        })
        
    # Sort by source
    data.sort(key=lambda x: x['source'])
    
    return jsonify({"code": 0, "data": data})

@bp.route('/api/source_rules', methods=['POST'])
@login_required
@admin_required
def api_source_rules():
    data = request.get_json(force=True) or {}
    source = data.get('source')
    domain = data.get('domain', '') # Optional domain
    
    if not source:
        return jsonify({"code": 1, "msg": "Source required"})
        
    from app.models import SourceBinding
    
    # Find binding matching source AND domain
    bindings = SourceBinding.query.filter_by(source_name=source, source_domain=domain).all()
    rule_ids = [b.rule_id for b in bindings]
    
    return jsonify({"code": 0, "data": rule_ids})

@bp.route('/api/bind_source', methods=['POST'])
@login_required
@admin_required
def api_bind_source():
    data = request.get_json(force=True) or {}
    
    # Support both single (old) and batch (new) formats
    sources = data.get('sources', []) # List of {source, domain}
    
    # Fallback for old format
    if not sources:
        single_source = data.get('source')
        single_domain = data.get('domain', '')
        if single_source:
            sources.append({'source': single_source, 'domain': single_domain})
            
    rule_ids = data.get('rule_ids', []) # List of ints
    
    if not sources:
        return jsonify({"code": 1, "msg": "No sources provided"})
        
    from app.models import SourceBinding
    
    try:
        for item in sources:
            src = item.get('source')
            dom = item.get('domain', '')
            if not src: continue
            
            # Clear existing bindings for this source+domain
            SourceBinding.query.filter_by(source_name=src, source_domain=dom).delete()
            
            # Add new bindings
            for rid in rule_ids:
                binding = SourceBinding(source_name=src, source_domain=dom, rule_id=rid)
                db.session.add(binding)
                
        db.session.commit()
        return jsonify({"code": 0, "msg": "Bound successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "msg": str(e)})

@bp.route('/api/auto_bind', methods=['POST'])
@login_required
@admin_required
def api_auto_bind():
    from app.models import CrawlRule, SourceBinding
    from sqlalchemy import func
    
    # 1. Get all items distinct (source, domain) using GROUP BY
    results = db.session.query(CrawlItem.source, func.min(CrawlItem.url))\
        .filter(CrawlItem.source != None, CrawlItem.source != "")\
        .group_by(CrawlItem.source).all()
    source_map = {}
    for r in results:
        source = r[0]
        url = r[1]
        domain = ''
        if url:
            try:
                domain = urlparse(url).netloc
            except:
                pass
        key = (source, domain)
        source_map[key] = True
        
    # 2. Get all rules
    rules = CrawlRule.query.all()
    
    count = 0
    
    for (source, domain) in source_map.keys():
        # If already bound, skip? Maybe we want to overwrite or fill missing?
        # Let's fill missing only
        existing = SourceBinding.query.filter_by(source_name=source, source_domain=domain).first()
        if existing:
            continue
            
        # Try to match
        matched_rule = None
        
        # Priority 1: Exact Domain Match
        if domain:
            for rule in rules:
                if rule.domain and rule.domain == domain:
                    matched_rule = rule
                    break
        
        # Priority 2: Partial Domain Match (Rule domain in Source domain or vice versa)
        if not matched_rule and domain:
            for rule in rules:
                if rule.domain and (rule.domain in domain or domain in rule.domain):
                    matched_rule = rule
                    break
                    
        # Priority 3: Name Match (Strict)
        if not matched_rule:
            for rule in rules:
                if rule.site_name and rule.site_name == source:
                    matched_rule = rule
                    break
                    
        # Priority 4: Name Match (Partial - Rule in Source)
        if not matched_rule:
             for rule in rules:
                if rule.site_name and rule.site_name in source:
                    matched_rule = rule
                    break
                
        if matched_rule:
            binding = SourceBinding(source_name=source, source_domain=domain, rule_id=matched_rule.id)
            db.session.add(binding)
            count += 1
            
    db.session.commit()
    return jsonify({"code": 0, "msg": f"Auto bound {count} sources"})

@bp.route('/api/smart_sniff', methods=['POST'])
@login_required
@admin_required
def api_smart_sniff():
    data = request.get_json(force=True) or {}
    url = data.get('url')
    
    if not url:
        return jsonify({"code": 1, "msg": "URL required"})
        
    from app.sniffer import SmartSniffer
    
    sniffer = SmartSniffer(url)
    result = sniffer.sniff()
    
    if not result:
        return jsonify({"code": 1, "msg": "Sniffing failed or could not fetch page"})
        
    return jsonify({
        "code": 0, 
        "data": {
            "title_xpath": result.get("title_xpath"),
            "content_xpath": result.get("content_xpath"),
            "site_name": result.get("site_name"),
            "domain": result.get("domain"),
            "headers": result.get("headers")
        }
    })

@bp.route('/api/dynamic_source/add', methods=['POST'])
@login_required
@admin_required
def api_dynamic_source_add():
    from app.models import CrawlSource
    data = request.get_json(force=True) or {}
    name = data.get('name')
    base_url = data.get('base_url')
    if not name or not base_url:
        return jsonify({"code":1, "msg":"name and base_url required"})
    import json
    src = CrawlSource(
        name=name,
        base_url=base_url,
        headers=json.dumps(data.get('headers') or {}, ensure_ascii=False),
        params=json.dumps(data.get('params') or {}, ensure_ascii=False),
        pagination=json.dumps(data.get('pagination') or {}, ensure_ascii=False),
        selectors=json.dumps(data.get('selectors') or {}, ensure_ascii=False),
        is_active=True
    )
    db.session.add(src)
    db.session.commit()
    return jsonify({"code":0, "msg":"Added"})

@bp.route('/api/delete', methods=['POST'])
@login_required
@admin_required
def api_delete():
    data = request.get_json(force=True) or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({"code": 1, "msg": "No ids provided"})
    
    try:
        CrawlItem.query.filter(CrawlItem.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({"code": 0, "msg": "Deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "msg": str(e)})

@bp.route('/api/update', methods=['POST'])
@login_required
@admin_required
def api_update():
    data = request.get_json(force=True) or {}
    id = data.get('id')
    if not id:
        return jsonify({"code": 1, "msg": "No id provided"})
        
    item = CrawlItem.query.get(id)
    if not item:
        return jsonify({"code": 1, "msg": "Item not found"})
        
    if 'title' in data:
        item.title = data['title']
    if 'deep_summary' in data:
        item.deep_summary = data['deep_summary']
        
    try:
        db.session.commit()
        return jsonify({"code": 0, "msg": "Updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "msg": str(e)})

@bp.route('/api/analyze', methods=['POST'])
@login_required
@admin_required
def api_analyze():
    data = request.get_json(force=True) or {}
    id = data.get('id')
    if not id:
        return jsonify({"code": 1, "msg": "No id provided"})
        
    # Placeholder for AI analysis
    # In the future, call AI service here
    
    return jsonify({
        "code": 0, 
        "msg": "Analysis request submitted (Placeholder)",
        "result": "AI analysis result will appear here..."
    })

@bp.route('/api/detail/<int:id>')
@login_required
def api_detail(id):
    from app.models import ArticleDetail
    detail = ArticleDetail.query.filter_by(crawl_item_id=id).first()
    if not detail:
        return jsonify({"code": 1, "msg": "Detail not found"})
    
    return jsonify({
        "code": 0,
        "data": {
            "title": detail.title,
            "content": detail.content,
            "created_at": detail.created_at.strftime('%Y-%m-%d %H:%M:%S') if detail.created_at else ''
        }
    })

@bp.route('/api/deep_crawl', methods=['POST'])
@login_required
@admin_required
def api_deep_crawl():
    data = request.get_json(force=True) or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({"code": 1, "msg": "No ids provided"})
        
    from app.models import CrawlRule
    from app.crawler import RuleCrawler
    import logging
    
    logger = logging.getLogger(__name__)
    
    success_count = 0
    errors = []
    
    items = CrawlItem.query.filter(CrawlItem.id.in_(ids)).all()
    for item in items:
        logger.info(f"Processing item {item.id}: {item.title} ({item.url})")
        
        rules = []
        
        # Calculate domain
        domain = ''
        if item.url:
            try:
                domain = urlparse(item.url).netloc
            except:
                pass
        
        # 1. Check Source Bindings (with domain)
        if item.source:
            from app.models import SourceBinding
            # Try exact match with domain
            bindings = SourceBinding.query.filter_by(source_name=item.source, source_domain=domain).all()
            if bindings:
                for b in bindings:
                    rules.append(b.rule)
                logger.info(f"Found {len(rules)} bound rules for source {item.source} ({domain})")
            else:
                # Try match without domain? No, user wants specific domain binding.
                pass

        # 2. Fallback to name match if no bindings
        if not rules:
            rule = None
            if item.source:
                rule = CrawlRule.query.filter_by(site_name=item.source.strip()).first()
                if rule:
                    logger.info(f"Matched rule by site_name: {rule.site_name}")
            
            # If no exact match by name, try domain match if url is available
            if not rule and domain:
                # Find rule where rule.domain is part of the item's domain
                rules_with_domain = CrawlRule.query.filter(CrawlRule.domain != None, CrawlRule.domain != "").all()
                for r in rules_with_domain:
                    if r.domain and r.domain in domain:
                        rule = r
                        logger.info(f"Matched rule by domain: {rule.site_name} ({rule.domain})")
                        break
            if rule:
                rules.append(rule)
                
        if rules:
            for rule in rules:
                try:
                    logger.info(f"Starting crawl with rule: {rule.site_name}")
                    crawler = RuleCrawler(rule)
                    result = crawler.fetch_detail(item.url)
                    
                    if result and result.get('content') and len(str(result.get('content')).strip()) > 10:
                        logger.info(f"Crawl successful. Title len: {len(result.get('title') or '')}, Content len: {len(result.get('content') or '')}")
                        
                        item.deep_summary = result.get('content', '')[:200] + '...' if result.get('content') else ''
                        item.deep_crawled = True # Explicitly set flag
                        
                        # Save to ArticleDetail
                        from app.models import ArticleDetail
                        detail = ArticleDetail.query.filter_by(crawl_item_id=item.id).first()
                        if not detail:
                            detail = ArticleDetail(crawl_item_id=item.id)
                        
                        detail.title = result.get('title') or item.title
                        detail.content = result.get('content', '')
                        db.session.add(detail)
                        success_count += 1
                        break # Stop after first success
                    else:
                         logger.warning(f"Crawl result empty or too short for item {item.id}")
                except Exception as e:
                    logger.error(f"Error crawling with rule {rule.id}: {e}")
                    
    db.session.commit()
    return jsonify({
        "code": 0, 
        "msg": f"Processed {len(items)} items. Success: {success_count}",
        "success_count": success_count
    })

@bp.route('/api/batch_generate_rules', methods=['POST'])
@login_required
def api_batch_generate_rules():
    data = request.get_json(force=True) or {}
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({"code": 1, "msg": "请选择数据"})
        
    items = CrawlItem.query.filter(CrawlItem.id.in_(ids)).all()
    
    success_count = 0
    skipped_count = 0
    failed_count = 0
    
    from app.sniffer import SmartSniffer
    from app.models import CrawlRule
    import json
    
    processed_domains = set()
    
    for item in items:
        if not item.url:
            failed_count += 1
            continue
            
        try:
            # Extract domain first to check duplicates before sniffing (save network)
            domain = ''
            try:
                domain = urlparse(item.url).netloc
            except:
                pass
                
            if domain:
                if domain in processed_domains:
                    skipped_count += 1
                    continue
                
                exists = CrawlRule.query.filter_by(domain=domain).first()
                if exists:
                    skipped_count += 1
                    continue
            
            # Sniff
            sniffer = SmartSniffer(item.url)
            res = sniffer.sniff()
            
            if res and res.get('title_xpath') and res.get('content_xpath'):
                # Name logic
                name = res.get('site_name') or item.source or res.get('domain') or 'Unknown Site'
                rule_domain = res.get('domain')
                
                if rule_domain:
                    processed_domains.add(rule_domain)
                    
                    # Double check if rule exists (in case domain extraction differed)
                    exists = CrawlRule.query.filter_by(domain=rule_domain).first()
                    if exists:
                        skipped_count += 1
                        continue
                
                rule = CrawlRule(
                    site_name=name,
                    domain=rule_domain,
                    title_xpath=res.get('title_xpath'),
                    content_xpath=res.get('content_xpath'),
                    headers=json.dumps(res.get('headers') or {}, ensure_ascii=False),
                    is_active=True
                )
                db.session.add(rule)
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            failed_count += 1
            
    db.session.commit()
    
    return jsonify({
        "code": 0,
        "msg": f"完成: 生成 {success_count} 个, 跳过 {skipped_count} 个, 失败 {failed_count} 个",
        "data": {"success": success_count, "skipped": skipped_count, "failed": failed_count}
    })
