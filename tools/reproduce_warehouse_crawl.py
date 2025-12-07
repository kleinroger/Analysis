import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import CrawlItem, CrawlRule, ArticleDetail
from app.crawler import RuleCrawler

# Configure logging to see the output from our changes
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_warehouse_logic():
    app = create_app()
    with app.app_context():
        print("=== Setting up test data ===")
        
        # 1. Ensure Rule Exists
        site_name = "金台资讯"
        rule = CrawlRule.query.filter_by(site_name=site_name).first()
        if not rule:
            print(f"Creating rule: {site_name}")
            rule = CrawlRule(
                site_name=site_name,
                domain="baijiahao.baidu.com",
                title_xpath="//h1/text() | //div[@class='article-title']/text()",
                content_xpath="//div[@class='article-content'] | //div[@id='article'] | //div[contains(@class, 'index-module_article-content')]"
            )
            db.session.add(rule)
            db.session.commit()
        else:
            print(f"Rule exists: {site_name}")
            
        # 2. Create/Get CrawlItem
        url = "https://baijiahao.baidu.com/s?id=1850536807759440270&wfr=spider&for=pc"
        item = CrawlItem.query.filter_by(url=url).first()
        if not item:
            print(f"Creating item: {url}")
            item = CrawlItem(
                title="Test Item",
                url=url,
                source=site_name,
                keyword="Test"
            )
            db.session.add(item)
            db.session.commit()
        else:
            print(f"Item exists: {item.id}")
            # Reset state
            item.deep_crawled = False
            item.deep_summary = None
            db.session.add(item)
            # Remove detail if exists
            detail = ArticleDetail.query.filter_by(crawl_item_id=item.id).first()
            if detail:
                db.session.delete(detail)
            db.session.commit()
            
        print(f"Testing warehouse deep crawl logic for item {item.id}...")
        
        # 3. Simulate api_deep_crawl logic (copy-paste key parts or invoke if possible, but invocation needs request context)
        # We will run the exact logic we added to routes.py to verify it works in this context
        
        # Match rule logic
        matched_rule = None
        if item.source:
            matched_rule = CrawlRule.query.filter_by(site_name=item.source.strip()).first()
            if matched_rule:
                print(f"Matched rule by site_name: {matched_rule.site_name}")
        
        if not matched_rule and item.url:
            from urllib.parse import urlparse
            try:
                domain = urlparse(item.url).netloc
                rules_with_domain = CrawlRule.query.filter(CrawlRule.domain != None, CrawlRule.domain != "").all()
                for r in rules_with_domain:
                    if r.domain and r.domain in domain:
                        matched_rule = r
                        print(f"Matched rule by domain: {matched_rule.site_name}")
                        break
            except Exception as e:
                print(f"Domain match error: {e}")
                
        if matched_rule:
            print(f"Starting crawl with rule: {matched_rule.site_name}")
            crawler = RuleCrawler(matched_rule)
            result = crawler.fetch_detail(item.url)
            
            if result and (result.get('title') or result.get('content')):
                print(f"Crawl successful!")
                print(f"Title: {result.get('title')}")
                print(f"Content length: {len(result.get('content', ''))}")
                
                # Verify it would be saved
                item.deep_summary = result.get('content', '')[:200] + '...'
                
                detail = ArticleDetail(crawl_item_id=item.id)
                detail.title = result.get('title') or item.title
                detail.content = result.get('content', '')
                db.session.add(detail)
                item.deep_crawled = True
                db.session.commit()
                print("Saved to database successfully.")
            else:
                print("Crawl returned empty result.")
        else:
            print("No rule found.")

if __name__ == "__main__":
    test_warehouse_logic()
