import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import CrawlRule, CrawlItem, ArticleDetail
from app.crawler import RuleCrawler
from urllib.parse import urlparse

def test_deep_crawl():
    app = create_app()
    with app.app_context():
        target_url = "https://www.scpublic.cn/news/getNewsDatail?id=850344"
        domain = "scpublic.cn"
        
        print(f"Testing deep crawl for: {target_url}")
        
        # 1. Check/Create Rule
        rule = CrawlRule.query.filter(CrawlRule.domain.contains(domain)).first()
        if not rule:
            print("Rule not found. Creating new rule for scpublic.cn...")
            # Based on typical structure for this site, or just generic placeholders that the user might expect to be tested/refined
            # I'll try to guess some XPaths or leave them empty if the crawler has auto-detection (the user prompt implies checking if matching works)
            # But usually we need XPaths. Let's try to inspect the site content first?
            # Actually, for this test, I should probably provide a rule that is likely to work or just a basic one.
            # Let's assume standard article structure.
            rule = CrawlRule(
                site_name="四川公共",
                domain="scpublic.cn",
                title_xpath="//h1/text() | //div[@class='title']/text()",
                content_xpath="//div[@class='content'] | //div[@id='content'] | //div[contains(@class, 'detail-content')]"
            )
            db.session.add(rule)
            db.session.commit()
            print(f"Created rule: {rule.site_name} (ID: {rule.id})")
        else:
            print(f"Found existing rule: {rule.site_name} (ID: {rule.id})")
            
        # 2. Create CrawlItem
        item = CrawlItem.query.filter_by(url=target_url).first()
        if not item:
            item = CrawlItem(
                title="Test Item",
                url=target_url,
                source="四川公共",
                keyword="test"
            )
            db.session.add(item)
            db.session.commit()
            print(f"Created test item (ID: {item.id})")
        else:
            print(f"Found existing item (ID: {item.id})")
            # Reset state
            item.deep_crawled = False
            if item.detail:
                db.session.delete(item.detail)
            db.session.commit()
            print("Reset item state")

        # 3. Execute Deep Crawl Logic (similar to routes.py)
        print("Executing deep crawl...")
        crawler = RuleCrawler(rule)
        try:
            result = crawler.fetch_detail(item.url)
            if result:
                print("Crawl successful!")
                print(f"Title: {result.get('title')}")
                print(f"Content length: {len(result.get('content', ''))}")
                
                # Save logic
                item.deep_summary = result.get('content', '')[:200] + '...' if result.get('content') else ''
                
                detail = ArticleDetail(crawl_item_id=item.id)
                detail.title = result.get('title') or item.title
                detail.content = result.get('content', '')
                db.session.add(detail)
                
                item.deep_crawled = True
                db.session.commit()
                print("Saved to database.")
            else:
                print("Crawl returned empty result.")
        except Exception as e:
            print(f"Crawl failed: {str(e)}")

        # 4. Verify
        saved_detail = ArticleDetail.query.filter_by(crawl_item_id=item.id).first()
        if saved_detail:
            print("-" * 30)
            print("VERIFICATION SUCCESSFUL")
            print(f"Saved Title: {saved_detail.title}")
            print(f"Saved Content Preview: {saved_detail.content[:100]}...")
        else:
            print("-" * 30)
            print("VERIFICATION FAILED: No detail record found.")

if __name__ == "__main__":
    test_deep_crawl()
