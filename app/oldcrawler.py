import requests
from bs4 import BeautifulSoup
import urllib.parse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaiduCrawler:
    def __init__(self):
        self.base_url = "https://www.baidu.com/s"
        self.enable_deep = False
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Cookie": "BIDUPSID=D48AC21A701043225723F7B0416A45A5; PSTM=1749868400; BD_UPN=1a314753; BAIDUID=D48AC21A70104322974B66FAE2F73383:SL=0:NR=10:FG=1; MAWEBCUID=web_YJdcNWbgVAvBDdOlAjnOFGURksbLStlKretXHCZPDmkKBoCWao; MCITY=-75%3A; newlogin=1; BDUSS=Bsb0RmVWp3c0NmMHNwOVpnVTZpSUU1Rn5IU1c1S29EVVJQYVI0ZWFnWEhDazVwSVFBQUFBJCQAAAAAAAAAAAEAAACr7QECeWFuZ2FodWkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMd9JmnHfSZpNX; BDUSS_BFESS=Bsb0RmVWp3c0NmMHNwOVpnVTZpSUU1Rn5IU1c1S29EVVJQYVI0ZWFnWEhDazVwSVFBQUFBJCQAAAAAAAAAAAEAAACr7QECeWFuZ2FodWkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMd9JmnHfSZpNX; BDORZ=FFFB88E999055A3F8A630C64834BD6D0; BAIDUID_BFESS=D48AC21A70104322974B66FAE2F73383:SL=0:NR=10:FG=1; ZFY=:BbjM:A1IBjzvZvV4stKekEFIixozKxmgJlX2ZrIwt9J0:C; PAD_BROWSER=1; baikeVisitId=19c653f4-0ad5-4da2-9e04-2e58f31d7020; BA_HECTOR=2k25a5800401842la58585858101a71kj3ceo25; BDRCVFR[S_ukKV6dOkf]=mk3SLVN4HKm; delPer=0; BD_CK_SAM=1; sug=3; sugstore=0; ORIGIN=0; bdime=0; pcMainBoxRec=1; Hm_lvt_aec699bb6442ba076c8981c6dc490771=1764522517,1764723037,1764774343,1764867492; Hm_lpvt_aec699bb6442ba076c8981c6dc490771=1764867492; HMACCOUNT=05A3307F71DF5B6F; COOKIE_SESSION=216_0_9_9_13_35_1_1_9_8_8_7_93153_0_12_0_1764867497_0_1764867485%7C9%2325100_26_1764063190%7C9; SMARTINPUT=1; H_PS_PSSID=60272_63144_66109_66213_66232_66288_66271_66393_66510_66516_66529_66552_66589_66591_66601_66606_66652_66671_66669_66694_66685_66720_66744_66623_66772_66787_66792_66747_66806_66799_66599_66814; BDRCVFR[C0p6oIjvx-c]=mk3SLVN4HKm; BDSVRTM=543; H_WISE_SIDS_BFESS=60272_63144_66109_66213_66232_66288_66271_66393_66510_66516_66529_66552_66589_66591_66601_66606_66671_66669_66694_66685_66720_66744_66623_66772_66787_66792_66747_66806_66799_66599_66814; H_WISE_SIDS=110085_646558_656456_657501_658259_660927_661764_667681_669527_670901_673682_674801_675352_675506_675212_675809_675859_676009_675980_675908_676212_676273_666750_676461_676562_676555_676127_675247_675234_676689_676614_676764_676857_677027_677273_677315_677403_677464_677421_677616_677703_677706_677593_677776_676148_653709_678146_678134_678171_678221_678243_677805_675106_678426_678495_678379_678374_678591_678602_678620_678646_678662_678547_678651_678777_678770_678783_678873_678878_678883_679007_679010_678968_679027_676609_678932_678934_679064_679061_679078_678980_679066_679285_679299_679191_678007_676451_678468_679433_679462_678255_679370_675092_677575_673654_679697_679720_679741_679734_679750_679772_679855_679891_679648_679702_680021_678740_680024_680040_680060_680093_679906_678498_680196_679575_680148; rsv_i=4a37IDi/Um8FhFA/RX7tpg0ba5QbvlI0aOU+DTe1xdBC8pz1USAM85WvKjGDw8aJDyP6zn5YNkzZtYSrEokr6WJacdMph6U; PSCBD=16%3A1%3A3; SE_LAUNCH=5%3A29414502073_16%3A29414502073%3A3; BAIDUID_REF=D48AC21A70104322974B66FAE2F73383:FG=1; BDPASSGATE=IlPT2AEptyoA_yiU4SDm3lIN8eDEUsCD34OtVlZi3ECGh67BmhH-4MxTFlrLN73r1iH1--3Cs1wDpj8tQlBigrEtqAMDtjNGfCXcxN727aLUOt-8-rce0rXoGFgNsA8PbRhL-3MEF3V4VFYKbRT9hNgAeOqsxRZIecrR5EDHiMfs2keRBWGFzYKIPoxkPG4fPNu5cPrlnygdPk_cWe8oTi_FgS1iVp1L7qaKiOMmPOD5qkoXGur_QhwlIYvPFXR8_Bjb12q770ys0yUG8XFYSkUtdEiV5sj9IUMMCsDeot2DNv0fJB7AUlPhAKcmb0PbLQdWKQ3zmtsGPTYyynZlJp-j0aLUOmvqNE95RrOGiBjZCXwVqlOMJezY97YzRv4Q4BRYZwNdSikErVaAreCmpSr2HwPgi_lwT0Ug_Sjn9Xgwfn63Gm4K6Hqzc7Rvu7O8ZmGX164p0LbnSIhKuuKyJaXaVKr9E6g2sESWh5DveTCHBfj6RMR7kzgCwnV7TXC3ceKbPjDfXPyKeLZfwrXqvszDu9STzTC3tT8PLOKi4fgZ0oUcmqV4CmjJzGy_eXxAO3bM8mvkE5fTnCdMwtyIjyZnlPA1FtZqZujjJPITwcSIkWwV0yYtpaTHDeAQXJjkufxGIvD0UY8Y1kD9X7lRgrtA2V4vIJSCvqTf1z1g3TWO1C8fG0xP55VKg7UWS_fgC5bxaNYMIliBp4AsP2qip7diFOEjEkV-y7zJ3-8KO4aBz4lJqUVu8ron4o8TYujezIQLoagqUyKuewfzOKytgJgVi9OIgQx9A0m-Omvk8FKyIBEq-nm4; ab_sr=1.0.1_NWMzMDc0NThiNjExYTNkNDU5OTNmYjkwNDM2ZWIyYjE1OGI4NWNiMDc5M2IzZGVhZjk3NDIyN2Q2NjY4ODBlODQ5MzE1NTI2NDc2YzE2NzBmZWYxNTA3NGM5NGZhMmZkMDE1NGI2ODIxZGIzNWViMzRjNjI5ZjE0OGQyOTkyNmMzMTEzY2IyODFlNTdlNTc0ODU5YmRjMmI2YTg1ZjA1Mw==",
            "Host": "www.baidu.com",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Not)A;Brand";v="24", "Chromium";v="116"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36 Core/1.116.586.400 QQBrowser/19.8.6883.400"
        }

    def _parse(self, soup):
        results = []
        news_items = soup.find_all('div', class_='result-op')
        if not news_items:
            titles = soup.find_all('h3', class_='news-title_1YtI1')
            if titles:
                news_items = [t.find_parent('div', class_='result-op') or t.parent for t in titles]
        if not news_items:
            potential_containers = soup.find_all('div', class_='c-container')
            if potential_containers:
                news_items = potential_containers
        if not news_items:
            news_items = soup.select('.result-op')
        for item in news_items:
            try:
                title_elem = item.find('h3', class_='news-title_1YtI1')
                if not title_elem:
                    title_elem = item.find('h3')
                title = title_elem.get_text(strip=True) if title_elem else ""
                link_elem = title_elem.find('a') if title_elem else None
                url = link_elem['href'] if link_elem and link_elem.has_attr('href') else ""
                source_elem = item.find('a', class_='c-color-gray') or item.find('span', class_='c-color-gray')
                source = source_elem.get_text(strip=True) if source_elem else ""
                img_elem = item.find('img', class_='c-img') or (item.find('div', class_='c-img-border').find('img') if item.find('div', class_='c-img-border') else None) or item.select_one('img')
                cover = ""
                if img_elem:
                    cover = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-thumb') or img_elem.get('data-actualsrc') or ""
                item_obj = {
                    "title": title,
                    "summary": "",
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
            resp = requests.get(url, headers=self.headers, timeout=6)
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
            resp = requests.get(url, headers=self.headers, timeout=8)
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
                response = requests.get(self.base_url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                last_text = response.text
                soup = BeautifulSoup(response.text, 'html.parser')
                page_items = self._parse(soup)
                for it in page_items:
                    key = it.get("url") or (it.get("title", "") + it.get("source", ""))
                    if key in seen:
                        continue
                    seen.add(key)
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
