import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import CrawlRule, CrawlItem, ArticleDetail
from app.crawler import RuleCrawler

def test_deep_crawl():
    app = create_app()
    with app.app_context():
        target_url = "https://baijiahao.baidu.com/s?id=1850536807759440270&wfr=spider&for=pc"
        site_name = "金台资讯"
        
        print(f"Testing deep crawl for: {target_url}")
        
        # 1. Check/Create Rule
        rule = CrawlRule.query.filter_by(site_name=site_name).first()
        if not rule:
            print(f"Rule '{site_name}' not found. Creating new rule...")
            # Baijiahao standard structure
            rule = CrawlRule(
                site_name=site_name,
                domain="baijiahao.baidu.com",
                title_xpath="//h1/text() | //div[@class='article-title']/text()",
                content_xpath="//div[@class='article-content'] | //div[@id='article'] | //div[contains(@class, 'index-module_article-content')]"
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
                title="Test Baijiahao Item",
                url=target_url,
                source=site_name,
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

        # 3. Execute Deep Crawl Logic
        print("Executing deep crawl...")
        # Enable debug logging for requests
        import logging
        logging.basicConfig(level=logging.DEBUG)
        
        crawler = RuleCrawler(rule)
        try:
            # Manually fetch to debug
            import requests
            resp = requests.get(item.url, headers=crawler.headers, timeout=15)
            print(f"Response status: {resp.status_code}")
            print(f"Response headers: {resp.headers}")
            print(f"Response encoding: {resp.encoding}")
            print(f"Response apparent_encoding: {resp.apparent_encoding}")
            
            # Force encoding if needed
            resp.encoding = resp.apparent_encoding
            
            print(f"Response len: {len(resp.text)}")
            # print(f"Response preview: {resp.text[:1000]}") # Comment out binary garbage
            
            from lxml import etree
            html = etree.HTML(resp.text)
            print("Testing title xpath...")
            ts = html.xpath(rule.title_xpath)
            print(f"Title XPath result: {ts}")
            
            print("Testing content xpath...")
            cs = html.xpath(rule.content_xpath)
            print(f"Content XPath result: {cs}")
            
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
