import requests
from lxml import etree
from urllib.parse import urlparse

class SmartSniffer:
    def __init__(self, url):
        self.url = url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.html_tree = None
        self.raw_html = None

    def fetch(self):
        try:
            resp = requests.get(self.url, headers=self.headers, timeout=15)
            resp.encoding = resp.apparent_encoding
            self.raw_html = resp.text
            self.html_tree = etree.HTML(resp.text)
            return True
        except Exception as e:
            print(f"Sniff fetch error: {e}")
            return False

    def sniff(self):
        if self.html_tree is None:
            if not self.fetch():
                return None

        # 1. Sniff Title
        title_xpath = self._sniff_title()
        
        # 2. Sniff Content
        content_xpath = self._sniff_content()

        # 3. Extract Site Name (Page Title) and Domain
        site_name = ""
        titles = self.html_tree.xpath('//title/text()')
        if titles:
            site_name = titles[0].strip()
            
        domain = ""
        try:
            domain = urlparse(self.url).netloc
        except:
            pass

        return {
            "title_xpath": title_xpath,
            "content_xpath": content_xpath,
            "site_name": site_name,
            "domain": domain,
            "headers": self.headers
        }

    def _sniff_title(self):
        """
        Heuristic:
        1. Check <h1 class="xxx-title-xxx">
        2. Check <h1>
        3. Check <div class="title">, <h2 class="title">
        4. Match text with <title> tag content (often includes site name, so partial match)
        """
        # Get page title from <title> tag for reference
        page_title = ""
        titles = self.html_tree.xpath('//title/text()')
        if titles:
            page_title = titles[0].strip()

        candidates = []
        
        # Priority 1: h1
        h1s = self.html_tree.xpath('//h1')
        for h1 in h1s:
            candidates.append((h1, 100))

        # Priority 2: Elements with 'title' in class or id
        class_titles = self.html_tree.xpath('//*[contains(@class, "title") or contains(@id, "title")]')
        for el in class_titles:
            candidates.append((el, 80))

        # Evaluate candidates
        best_xpath = None
        best_score = 0

        for el, base_score in candidates:
            # Extract text
            text = "".join(el.xpath('.//text()')).strip()
            if not text:
                continue
            
            score = base_score
            # Bonus if text is similar to page title
            if page_title and (text in page_title or page_title in text):
                score += 50
            
            # Penalty if text is too short or too long
            if len(text) < 5:
                score -= 50
            if len(text) > 100:
                score -= 20

            if score > best_score:
                best_score = score
                best_xpath = self._generate_xpath(el)
                # Append /text() to make it a text extractor
                # But wait, RuleCrawler logic handles elements too. 
                # Ideally we want the element xpath, logic in RuleCrawler extracts text.
                # But standard format often includes /text()
                # Let's stick to element xpath for robustness, 
                # but wait, app/crawler.py fetch_detail logic:
                # if self.rule.title_xpath: ... html.xpath(self.rule.title_xpath) ... if isinstance(ts[0], str)...
                # So if we return element xpath, ts[0] is element, code does "".join(ts[0].xpath('.//text()'))
                # So returning element xpath is safer.

        return best_xpath

    def _sniff_content(self):
        """
        Heuristic:
        1. Find container with most <p> tags or most text length.
        2. Check common class/id names: content, article, main, news-body
        """
        candidates = []
        
        # Gather all divs, articles, sections
        containers = self.html_tree.xpath('//div | //article | //section | //td')
        
        for c in containers:
            # Score based on text length and p tags
            text_len = len("".join(c.xpath('.//text()')).strip())
            p_count = len(c.xpath('.//p'))
            
            score = 0
            if text_len > 200:
                score += min(text_len / 10, 200) # Cap length score
            else:
                continue # Too short
            
            score += p_count * 20
            
            # Boost for class/id names
            cls = c.get('class', '') or ''
            id_ = c.get('id', '') or ''
            keywords = ['content', 'article', 'detail', 'news_body', 'main']
            if any(k in cls.lower() for k in keywords) or any(k in id_.lower() for k in keywords):
                score += 100
                
            # Penalty for link density (navigation menus often have text but lots of links)
            links = c.xpath('.//a')
            link_text_len = sum([len("".join(a.xpath('.//text()')).strip()) for a in links])
            if text_len > 0:
                link_density = link_text_len / text_len
                if link_density > 0.5:
                    score -= 500 # Heavy penalty for nav/lists
            
            candidates.append((c, score))
            
        # Find best
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            best_el = candidates[0][0]
            return self._generate_xpath(best_el)
            
        return None

    def _generate_xpath(self, element):
        """
        Generate robust XPath. Copied/Adapted from RuleCrawler.
        """
        if element is None:
            return None
            
        # 1. Try ID (if it looks unique/meaningful, not auto-generated)
        id_ = element.get('id')
        if id_ and not any(x in id_ for x in ['ember', 'react', 'vue', 'random', 'idx']):
            return f"//*[@id='{id_}']"
            
        # 2. Try Class (if specific enough)
        cls = element.get('class')
        if cls:
            # Take the most specific-looking class (often the first or longest?)
            # Avoid common grid classes
            classes = cls.split()
            valid_classes = [c for c in classes if c not in ['row', 'col', 'container', 'wrapper', 'clearfix']]
            if valid_classes:
                target_cls = valid_classes[0]
                return f"//{element.tag}[contains(@class, '{target_cls}')]"
                
        # 3. Fallback to lxml path (absolute path) - simplified
        # lxml getpath usually returns /html/body/div[1]/...
        try:
            tree = element.getroottree()
            return tree.getpath(element)
        except:
            return f"//{element.tag}"
