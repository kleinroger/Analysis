import requests
from bs4 import BeautifulSoup
import urllib.parse
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaiduCrawler:
    def __init__(self):
        self.base_url = "https://www.baidu.com/s"
        self.enable_deep = False
        self.headers = self._build_headers()
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _build_headers(self):
        ua = os.environ.get(
            "BAIDU_UA",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
        )
        # Use the provided cookie as default if env var is not set
        default_cookie = "ORIGIN=0; bdime=0; BDUSS=lXV0RnY3RSY1ZVfi1mQ3lLZ0FFNU5GVDZWbzUyek5oQzJKSG9GZUpTS1VSREJvSVFBQUFBJCQAAAAAAQAAAAEAAAAKAakOsru-9WJ1anVlbGoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJS3CGiUtwhob1; PSTM=1764816623; BD_UPN=12314753; BIDUPSID=A29BFC946D0D17CF52697FF6CBDCEF08; BDORZ=FFFB88E999055A3F8A630C64834BD6D0; sug=3; sugstore=0; H_PS_645EC=0a72NDDj6cHIl8eMo8XLBnEGf8DtzWhQXj0lArmkrl9J5W4gRTtlHiSY2uTcACH2rQKAIgo; BDUSS_BFESS=lXV0RnY3RSY1ZVfi1mQ3lLZ0FFNU5GVDZWbzUyek5oQzJKSG9GZUpTS1VSREJvSVFBQUFBJCQAAAAAAQAAAAEAAAAKAakOsru-9WJ1anVlbGoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJS3CGiUtwhob1; BAIDUID=DFC91FFEFCC05ACF1B358570B83C3FCC:FG=1; H_WISE_SIDS=66101_66109_66189_66233_66203_66285_66259_66393_66464_66515_66529_66550_66584_66578_66593_66615_66654_66664_66672_66666_66697_66718_66744_66771_66787_66792_66800_66803_66599; BAIDUID_BFESS=DFC91FFEFCC05ACF1B358570B83C3FCC:FG=1; BA_HECTOR=a5ala585ak0g852l00802l0g242h801kj1tqg25; ZFY=nTmFFohdGanMF985RwXkiAH2ZbpNtVOe1U:ASc7zlIGk:C; BDRCVFR[C0p6oIjvx-c]=mbxnW11j9Dfmh7GuZR8mvqV; H_PS_PSSID=60279_63144_64005_65312_66103_66107_66215_66192_66201_66163_66282_66253_66393_66516_66529_66546_66585_66578_66592_66600_66641_66653_66682_66674_66670_66689_66720_66743_66792_66804_66599; delPer=0; BD_CK_SAM=1; PSINO=1; arialoadData=false; BDSVRTM=570"
        cookie = os.environ.get("BAIDU_COOKIE", default_cookie)
        
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Cookie": cookie,
            "Host": "www.baidu.com",
            "Pragma": "no-cache",
            "Referer": "https://news.baidu.com/",
            "Sec-Ch-Ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": ua,
        }

    def _resolve_baidu_link(self, url):
        try:
            from urllib.parse import urlparse
            p = urlparse(url)
            if p.netloc == "www.baidu.com" and p.path.startswith("/link"):
                r = self.session.get(url, allow_redirects=True, timeout=8)
                return r.url or url
        except Exception:
            return url
        return url

    def _parse(self, soup):
        results = []
        # Robust parsing strategy from old crawler
        # 1. Try standard result-op
        news_items = soup.find_all('div', class_='result-op')
        
        # 2. Fallback: Try finding titles and getting parents
        if not news_items:
            titles = soup.find_all('h3', class_='news-title_1YtI1')
            if titles:
                news_items = [t.find_parent('div', class_='result-op') or t.parent for t in titles]
                
        # 3. Fallback: Try c-container (older standard)
        if not news_items:
            news_items = soup.find_all('div', class_='c-container')
            
        # 4. Fallback: Try select (modern/generic)
        if not news_items:
            news_items = soup.select('.result-op, .c-container, .new-pmd')

        for item in news_items:
            try:
                # Try multiple title selectors
                title_elem = item.select_one('.news-title_1YtI1, h3.c-title, h3.t, h3')
                if not title_elem:
                    continue
                
                link_elem = title_elem.find('a')
                if not link_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                url = link_elem.get('href')
                if not url:
                    continue
                url = self._resolve_baidu_link(url)
                
                # Try multiple source selectors
                source_elem = item.select_one('.c-color-gray, .news-source, .c-source, .source-text_3o2Yd')
                source = source_elem.get_text(strip=True) if source_elem else "Baidu News"
                
                # Try multiple image selectors
                img_elem = item.select_one('.c-img, img.c-img')
                cover = ""
                if img_elem:
                    cover = img_elem.get('src') or img_elem.get('data-src') or ""
                
                # Try summary extraction
                summary_elem = item.select_one('.c-font-normal-three, .c-span18, .content-right_8Zs40, .c-abstract')
                summary = summary_elem.get_text(strip=True) if summary_elem else ""

                item_obj = {
                    "title": title,
                    "summary": summary,
                    "cover": cover,
                    "url": url,
                    "source": source
                }
                
                if not self._is_dirty(item_obj):
                    results.append(item_obj)
            except Exception as e:
                logger.error(f"Error parsing item: {e}")
                continue
        return results

    def _is_dirty(self, item):
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

    def _enrich(self, item):
        if not self.enable_deep:
            return item
        try:
            url = item.get("url")
            if not url:
                return item
            resp = self.session.get(url, timeout=6)
            soup = BeautifulSoup(resp.text, 'html.parser')
            if not item.get("cover"):
                img = soup.find('meta', attrs={"property": "og:image"}) or soup.find('meta', attrs={"name": "twitter:image"})
                if img and img.get('content'):
                    item["cover"] = img.get('content')
                else:
                    link_img = soup.find('link', rel="image_src")
                    if link_img and link_img.get('href'):
                        item["cover"] = link_img.get('href')
                    else:
                        any_img = soup.find('img')
                        if any_img:
                            src = any_img.get('src') or any_img.get('data-src') or any_img.get('data-actualsrc')
                            if src:
                                item["cover"] = urllib.parse.urljoin(url, src)
        except Exception:
            pass
        return item

    def _fetch_detail(self, item):
        if not self.enable_deep:
            return item
        try:
            url = item.get("url")
            if not url:
                return item
            resp = self.session.get(url, timeout=8)
            soup = BeautifulSoup(resp.text, 'html.parser')
            text = ""
            art = soup.find('article')
            if art:
                text = art.get_text("\n", strip=True)
            if not text:
                container = soup.find('div', class_='content') or soup.find('div', class_='article') or soup.find('div', id='content') or soup.find('div', id='article')
                if container:
                    text = container.get_text("\n", strip=True)
            if not text:
                ps = soup.find_all('p')
                if ps:
                    buf = []
                    for p in ps[:20]:
                        t = p.get_text(strip=True)
                        if t:
                            buf.append(t)
                    text = "\n".join(buf)
            if text:
                item["deep_summary"] = text[:2000]
            if not item.get("deep_cover"):
                meta_img = soup.find('meta', attrs={"property": "og:image"}) or soup.find('meta', attrs={"name": "twitter:image"})
                if meta_img and meta_img.get('content'):
                    item["deep_cover"] = meta_img.get('content')
                elif item.get("cover"):
                    item["deep_cover"] = item.get("cover")
                else:
                    any_img = soup.find('img')
                    if any_img:
                        src = any_img.get('src') or any_img.get('data-src') or any_img.get('data-actualsrc')
                        if src:
                            item["deep_cover"] = urllib.parse.urljoin(url, src)
        except Exception:
            pass
        return item

    def crawl(self, keyword, limit=30, max_pages=5):
        try:
            all_results = []
            seen = set()
            last_text = ""
            for page_index in range(max_pages):
                pn = page_index * 10
                params = {
                    "rtt": "1",
                    "bsst": "1",
                    "cl": "2",
                    "tn": "news",
                    "rsv_dl": "ns_pc",
                    "word": keyword,
                    "pn": pn
                }
                response = self.session.get(self.base_url, params=params, timeout=10)
                response.raise_for_status()
                last_text = response.text
                soup = BeautifulSoup(response.text, 'html.parser')
                page_items = self._parse(soup)
                enrich_budget = 12
                for it in page_items:
                    key = it.get("url") or (it.get("title", "") + it.get("source", ""))
                    if key in seen:
                        continue
                    seen.add(key)
                    if (not it.get("cover")) and enrich_budget > 0:
                        it = self._enrich(it)
                        enrich_budget -= 1
                    all_results.append(it)
                    if len(all_results) >= limit:
                        break
                if len(all_results) >= limit:
                    break
            return all_results
        except Exception:
            return []

class XinhuaCrawler:
    def __init__(self):
        self.base_url = "http://sc.news.cn/scyw.htm"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        }

    def _is_dirty(self, item):
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

    def _enrich(self, item):
        try:
            url = item.get("url")
            if not url:
                return item
            resp = requests.get(url, headers=self.headers, timeout=8)
            soup = BeautifulSoup(resp.text, 'html.parser')
            if not item.get("cover"):
                img = soup.find('meta', attrs={"property": "og:image"}) or soup.find('meta', attrs={"name": "twitter:image"})
                if img and img.get('content'):
                    item["cover"] = img.get('content')
                else:
                    link_img = soup.find('link', rel="image_src")
                    if link_img and link_img.get('href'):
                        item["cover"] = link_img.get('href')
                    else:
                        any_img = soup.find('img')
                        if any_img:
                            src = any_img.get('src') or any_img.get('data-src') or any_img.get('data-actualsrc')
                            if src:
                                item["cover"] = urllib.parse.urljoin(url, src)
        except Exception:
            pass
        return item

    def _parse(self, soup):
        results = []
        seen = set()
        for a in soup.select('a[href]'):
            href = a.get('href') or ''
            if not href:
                continue
            if 'news.cn' not in href:
                continue
            if href.startswith('javascript'):
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 6:
                continue
            if href in seen:
                continue
            seen.add(href)
            img = a.find('img') or (a.find_parent('li').find('img') if a.find_parent('li') else None)
            cover = ""
            if img:
                src = img.get('src') or img.get('data-src') or img.get('data-actualsrc') or ""
                if src:
                    cover = urllib.parse.urljoin(self.base_url, src)
            item_obj = {
                "title": title,
                "summary": "",
                "cover": cover,
                "url": urllib.parse.urljoin(self.base_url, href),
                "source": "新华网"
            }
            if not self._is_dirty(item_obj):
                results.append(item_obj)
        return results

    def crawl(self, keyword, limit=30, max_pages=1):
        try:
            all_results = []
            import requests
            resp = requests.get(self.base_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            page_items = self._parse(soup)
            seen = set()
            enrich_budget = 15
            for it in page_items:
                key = it.get("url") or it.get("title", "")
                if key in seen:
                    continue
                seen.add(key)
                if (not it.get("cover")) and enrich_budget > 0:
                    it = self._enrich(it)
                    enrich_budget -= 1
                all_results.append(it)
                if len(all_results) >= limit:
                    break
            return all_results
        except Exception:
            return []

class ChinaSoCrawler:
    def __init__(self):
        self.base_url = "http://www.chinaso.com/newssearch/all/allResults"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Host": "www.chinaso.com",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        }

    def _is_dirty(self, item):
        c = 0
        if not item.get("url"):
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

    def _parse(self, soup):
        results = []
        seen = set()
        for a in soup.select('a[href]'):
            href = a.get('href') or ''
            if not href:
                continue
            if href.startswith('javascript'):
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 6:
                continue
            parent = a.find_parent(['li','div'])
            img = None
            if parent:
                img = parent.find('img')
            cover = ""
            if img:
                cover = img.get('src') or img.get('data-src') or img.get('data-actualsrc') or ""
            try:
                import urllib.parse as up
                full_url = up.urljoin(self.base_url, href)
            except Exception:
                full_url = href
            try:
                from urllib.parse import urlparse
                host = urlparse(full_url).netloc or ""
            except Exception:
                host = ""
            item_obj = {
                "title": title,
                "summary": "",
                "cover": cover,
                "url": full_url,
                "source": host or "中国搜索"
            }
            key = item_obj["url"]
            if key in seen:
                continue
            seen.add(key)
            if not self._is_dirty(item_obj):
                results.append(item_obj)
            if len(results) >= 60:
                break
        return results

    def crawl(self, keyword, limit=30, max_pages=3):
        try:
            import requests
            from bs4 import BeautifulSoup
            items = []
            seen = set()
            for page_index in range(max_pages):
                pn = page_index + 1
                params = {"pn": pn, "force": 0, "q": keyword}
                resp = requests.get(self.base_url, headers=self.headers, params=params, timeout=10)
                soup = BeautifulSoup(resp.text, 'html.parser')
                page_items = self._parse(soup)
                for it in page_items:
                    key = it.get("url") or (it.get("title", "") + it.get("source", ""))
                    if key in seen:
                        continue
                    seen.add(key)
                    if keyword:
                        try:
                            if keyword not in it.get("title", ""):
                                continue
                        except Exception:
                            pass
                    items.append(it)
                    if len(items) >= limit:
                        break
                if len(items) >= limit:
                    break
            return items
        except Exception:
            return []

class SinaCrawler:
    def __init__(self):
        self.base_url = "https://search.sina.com.cn/news"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        }

    def _is_dirty(self, item):
        c = 0
        if not item.get("url"):
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

    def _parse(self, soup):
        results = []
        seen = set()
        
        # Select result boxes
        items = soup.find_all('div', class_='box-result')
        
        for item in items:
            try:
                # Title & URL
                h2 = item.find('h2')
                if not h2: continue
                
                a = h2.find('a')
                if not a: continue
                
                title = a.get_text(strip=True)
                url = a.get('href')
                
                if not url or not title:
                    continue
                
                if url in seen:
                    continue
                seen.add(url)
                
                # Summary
                summary_p = item.find('p', class_='content')
                summary = summary_p.get_text(strip=True) if summary_p else ""
                
                # Cover Image
                cover = ""
                img_div = item.find('div', class_='r-img')
                if img_div:
                    img = img_div.find('img')
                    if img:
                        cover = img.get('src') or img.get('data-src') or ""
                        # Handle relative URLs if any (though Sina usually gives absolute)
                        if cover and cover.startswith('//'):
                            cover = 'https:' + cover
                
                # Source
                source = "新浪新闻"
                time_span = item.find('span', class_='fgray_time')
                if time_span:
                    # Format is typically "Source Name   Time" e.g., "川观新闻   18分钟前"
                    full_text = time_span.get_text(strip=True)
                    # Simple split by space and take the first part
                    parts = full_text.split()
                    if parts:
                        source = parts[0]
                
                item_obj = {
                    "title": title,
                    "summary": summary,
                    "cover": cover,
                    "url": url,
                    "source": source
                }
                
                if not self._is_dirty(item_obj):
                    results.append(item_obj)
                    
            except Exception as e:
                logger.error(f"Error parsing Sina item: {e}")
                continue
                
        return results

    def crawl(self, keyword, limit=30, max_pages=3):
        try:
            import requests
            from bs4 import BeautifulSoup
            
            all_results = []
            seen_urls = set()
            
            for page in range(max_pages):
                params = {
                    "q": keyword,
                    "c": "news",
                    "from": "channel",
                    "ie": "utf-8",
                    "page": page + 1
                }
                
                try:
                    resp = requests.get(self.base_url, params=params, headers=self.headers, timeout=10)
                    
                    # Handle encoding manually if needed, but requests usually does OK if headers are right
                    # Sina might return ISO-8859-1 as default guess if header missing charset
                    if resp.encoding == 'ISO-8859-1':
                        resp.encoding = resp.apparent_encoding
                        
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    page_items = self._parse(soup)
                    
                    if not page_items:
                        break
                        
                    for it in page_items:
                        if it['url'] in seen_urls:
                            continue
                        seen_urls.add(it['url'])
                        all_results.append(it)
                        
                        if len(all_results) >= limit:
                            break
                    
                    if len(all_results) >= limit:
                        break
                        
                except Exception as e:
                    logger.error(f"Error crawling Sina page {page+1}: {e}")
                    continue
                    
            return all_results
            
        except Exception as e:
            logger.error(f"Sina crawler fatal error: {e}")
            return []

class DynamicCrawler:
    def __init__(self, config):
        self.base_url = config.get("base_url")
        self.headers = config.get("headers") or {}
        self.params = config.get("params") or {}
        self.pagination = config.get("pagination") or {}
        self.selectors = config.get("selectors") or {}

    def _is_dirty(self, item):
        c = 0
        if not item.get("url"):
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

    def _parse(self, soup):
        items = []
        cont_sel = self.selectors.get("container")
        title_sel = self.selectors.get("title")
        link_sel = self.selectors.get("link")
        source_sel = self.selectors.get("source")
        img_sel = self.selectors.get("image")
        containers = soup.select(cont_sel) if cont_sel else []
        seen = set()
        for item in containers:
            t = item.select_one(title_sel) if title_sel else None
            title = t.get_text(strip=True) if t else ""
            a = item.select_one(link_sel) if link_sel else None
            href = a.get("href") if a and a.has_attr("href") else ""
            s = item.select_one(source_sel) if source_sel else None
            source = s.get_text(strip=True) if s else ""
            cover = ""
            img = item.select_one(img_sel) if img_sel else None
            if img:
                cover = img.get("src") or img.get("data-src") or img.get("data-actualsrc") or ""
            u = href
            obj = {"title": title, "summary": "", "cover": cover, "url": u, "source": source}
            k = obj["url"] or (obj["title"] + obj["source"])
            if k in seen:
                continue
            seen.add(k)
            if not self._is_dirty(obj):
                items.append(obj)
        return items

    def crawl(self, keyword, limit=30, max_pages=5):
        try:
            import requests
            from bs4 import BeautifulSoup
            items = []
            seen = set()
            p_name = self.pagination.get("param")
            p_start = int(self.pagination.get("start", 0))
            p_step = int(self.pagination.get("step", 1))
            kw_param = self.params.get("keyword_param")
            base_params = {k: v for k, v in self.params.items() if k != "keyword_param"}
            for i in range(max_pages):
                params = dict(base_params)
                if kw_param:
                    params[kw_param] = keyword
                if p_name:
                    params[p_name] = p_start + i * p_step
                resp = requests.get(self.base_url, headers=self.headers, params=params, timeout=10)
                soup = BeautifulSoup(resp.text, "html.parser")
                page_items = self._parse(soup)
                for it in page_items:
                    k = it.get("url") or (it.get("title", "") + it.get("source", ""))
                    if k in seen:
                        continue
                    seen.add(k)
                    items.append(it)
                    if len(items) >= limit:
                        break
                if len(items) >= limit:
                    break
            return items
        except Exception:
            return []

# Simple test if run directly
if __name__ == "__main__":
    crawler = BaiduCrawler()
    data = crawler.crawl("西昌")
    for item in data:
        print(item)

class RuleCrawler:
    def __init__(self, rule):
        self.rule = rule
        self.headers = {}
        if rule.headers:
            import json
            try:
                self.headers = json.loads(rule.headers)
            except:
                pass
        # Ensure basic headers if missing
        if not self.headers.get('User-Agent'):
            self.headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"

    def _generate_xpath(self, element):
        """Generate a simple, robust XPath for an element."""
        if element is None:
            return None
        # Try ID
        if element.get('id'):
            return f"//*[@id='{element.get('id')}']"
        # Try Class (first class)
        if element.get('class'):
            cls = element.get('class').split()[0]
            return f"//{element.tag}[contains(@class, '{cls}')]"
        # Tag fallback for specific tags
        if element.tag in ['h1', 'article']:
            return f"//{element.tag}"
        # Fallback to lxml path
        try:
            return element.getroottree().getpath(element)
        except:
            return None

    def fetch_detail(self, url):
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            resp.encoding = resp.apparent_encoding # Handle encoding automatically
            
            from lxml import etree
            html = etree.HTML(resp.text)
            
            title = ""
            content = ""
            
            # 1. Try configured Title XPath
            if self.rule.title_xpath:
                # Support multiple XPaths separated by |
                # lxml xpath supports | operator naturally, but we might need to be careful
                ts = html.xpath(self.rule.title_xpath)
                if ts:
                    # Handle various xpath return types (element or string)
                    if isinstance(ts[0], str):
                        title = ts[0].strip()
                    elif hasattr(ts[0], 'text'):
                        # Try to get all text inside the title element, not just direct text
                        # This helps when title has spans or other tags inside
                        title = "".join(ts[0].xpath('.//text()')).strip()
                        
            # 2. Try configured Content XPath
            if self.rule.content_xpath:
                cs = html.xpath(self.rule.content_xpath)
                if cs:
                    # Usually content is a container, get all text
                    if hasattr(cs[0], 'xpath'):
                        # Get all text nodes under this element
                        texts = cs[0].xpath('.//text()')
                        content = "\n".join([t.strip() for t in texts if t.strip()])
                    elif isinstance(cs[0], str):
                        content = cs[0].strip()

            # 3. Automatic Rule Update Detection
            new_title_xpath = None
            new_content_xpath = None
            
            # If configured title failed (empty) but rule exists
            if self.rule.title_xpath and not title:
                # Heuristic: Look for h1 or class/id containing "title"
                candidates = html.xpath('//h1 | //*[contains(@class, "title")] | //*[@id="title"]')
                for c in candidates:
                    t_text = ""
                    if hasattr(c, 'text') and c.text:
                        t_text = c.text.strip()
                    if t_text and len(t_text) > 5: # Valid title usually > 5 chars
                        title = t_text
                        new_title_xpath = self._generate_xpath(c)
                        break
            
            # If configured content failed (empty) but rule exists
            if self.rule.content_xpath and not content:
                # Heuristic: Look for article, content containers
                candidates = html.xpath('//article | //*[contains(@class, "content")] | //*[contains(@class, "article")] | //*[@id="content"] | //*[@id="article"]')
                best_candidate = None
                max_len = 0
                for c in candidates:
                    texts = c.xpath('.//text()')
                    full_text = "\n".join([t.strip() for t in texts if t.strip()])
                    if len(full_text) > max_len:
                        max_len = len(full_text)
                        best_candidate = c
                
                if best_candidate is not None and max_len > 50: # Content usually > 50 chars
                    texts = best_candidate.xpath('.//text()')
                    content = "\n".join([t.strip() for t in texts if t.strip()])
                    new_content_xpath = self._generate_xpath(best_candidate)
                        
            return {
                "title": title,
                "content": content,
                "new_title_xpath": new_title_xpath,
                "new_content_xpath": new_content_xpath
            }
        except Exception as e:
            logger.error(f"Rule crawl error for {url}: {e}")
            return None
