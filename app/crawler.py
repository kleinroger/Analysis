import os
import requests
from bs4 import BeautifulSoup, Comment
import json

def crawl_baidu_news(keyword: str, pn: int = 0):
    url = "https://www.baidu.com/s"
    params = {
        "rtt": "1",
        "bsst": "1",
        "cl": "2",
        "tn": "news",
        "rsv_dl": "ns_pc",
        "word": keyword
    }
    try:
        pn_int = int(pn)
    except Exception:
        pn_int = 0
    if pn_int < 0:
        pn_int = 0
    if pn_int > 200:
        pn_int = 200
    params["pn"] = pn_int
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "no-cache",
        "connection": "keep-alive",
        "host": "www.baidu.com",
        "pragma": "no-cache",
        "referer": "https://news.baidu.com/",
        "sec-ch-ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-site",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
    }
    cookie = os.environ.get("BAIDU_COOKIE")
    if cookie:
        headers["cookie"] = cookie
    results = []
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        containers = soup.find_all("div", class_="c-container")
        if not containers:
            containers = soup.find_all("div", class_="result-op")
        for item in containers:
            obj = {}
            comment = item.find(string=lambda t: isinstance(t, Comment) and "s-data:" in t)
            if comment:
                try:
                    data_str = comment.strip().replace("s-data:", "", 1)
                    data = json.loads(data_str)
                    obj["title"] = data.get("title", "").replace("<em>", "").replace("</em>", "")
                    obj["summary"] = data.get("summary", "").replace("<em>", "").replace("</em>", "")
                    obj["cover"] = data.get("leftImgSrc", "")
                    obj["original_url"] = data.get("titleUrl", "")
                    obj["source"] = data.get("sourceName", "")
                    if obj.get("title") and obj.get("original_url") and obj.get("cover"):
                        results.append(obj)
                        continue
                except Exception:
                    pass
            try:
                title_tag = item.find("h3")
                if title_tag:
                    obj["title"] = title_tag.get_text(strip=True)
                    a_tag = title_tag.find("a")
                    if a_tag:
                        obj["original_url"] = a_tag.get("href", "")
                summary_div = item.find("div", class_="c-summary")
                if summary_div:
                    obj["summary"] = summary_div.get_text(strip=True)
                img_tag = item.find("img")
                if img_tag:
                    obj["cover"] = img_tag.get("src", "")
                source_div = item.find("div", class_="c-author") or item.find("span", class_="c-color-gray")
                if source_div:
                    obj["source"] = source_div.get_text(strip=True)
                if obj.get("title") and obj.get("original_url") and obj.get("cover"):
                    results.append(obj)
            except Exception:
                pass
    except Exception:
        pass
    return results

def crawl_sina_news(keyword: str, page: int = 1, size: int = 10):
    url = "https://search.sina.com.cn/news"
    try:
        p = int(page)
    except Exception:
        p = 1
    if p < 1:
        p = 1
    try:
        sz = int(size)
    except Exception:
        sz = 10
    if sz < 1:
        sz = 10
    if sz > 20:
        sz = 20
    params = {
        "q": keyword,
        "c": "news",
        "page": p,
        "num": sz
    }
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9",
        "referer": "https://search.sina.com.cn/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    results = []
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        items = []
        items.extend(soup.find_all("div", class_=lambda c: c and ("box-result" in c or "result" in c)))
        items.extend(soup.select(".box-result, .result") or [])
        seen = set()
        for it in items:
            a = it.find("a")
            if not a:
                continue
            href = a.get("href") or ""
            title = a.get_text(strip=True)
            if not href or not title:
                continue
            if href in seen:
                continue
            seen.add(href)
            original_url = href if href.startswith("http") else ("https://search.sina.com.cn/" + href.lstrip("/"))
            summary = ""
            s = it.find("p") or it.find("div")
            if s:
                summary = s.get_text(strip=True)
            img = it.find("img")
            cover = img.get("src") if img else ""
            obj = {
                "title": title,
                "summary": summary,
                "cover": cover,
                "original_url": original_url,
                "source": "新浪新闻"
            }
            if obj.get("title") and obj.get("original_url") and obj.get("cover"):
                results.append(obj)
    except Exception:
        pass
    return results[:sz]


def crawl_sohu_news(keyword: str, offset: int = 0, limit: int = 10):
    url = "https://search.sohu.com/"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9",
        "referer": "https://search.sohu.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    results = []
    try:
        try:
            page = (int(offset) // max(int(limit), 1)) + 1
        except Exception:
            page = 1
        params = {"keyword": keyword, "p": page}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        items = []
        items.extend(soup.find_all("div", class_=lambda c: c and ("box" in c or "result" in c or "news" in c or "item" in c)))
        items.extend(soup.select(".news-box .box, .result, .result-item, .news-item") or [])
        seen = set()
        for it in items:
            a = it.find("a")
            if not a:
                continue
            href = (a.get("href") or "").strip()
            title = a.get_text(strip=True)
            if not href or not title:
                continue
            if href in seen:
                continue
            seen.add(href)
            original_url = href if href.startswith("http") else ("https://search.sohu.com/" + href.lstrip("/"))
            s = it.find("p") or it.find("div")
            summary = s.get_text(strip=True) if s else ""
            img = it.find("img")
            cover = (img.get("src") or "").strip() if img else ""
            if cover and not (cover.startswith("http://") or cover.startswith("https://")):
                cover = "https://search.sohu.com/" + cover.lstrip("/")
            text = (title or "") + " " + (summary or "")
            if keyword and keyword not in text:
                continue
            obj = {
                "title": title,
                "summary": summary,
                "cover": cover,
                "original_url": original_url,
                "source": "搜狐新闻"
            }
            if obj.get("title") and obj.get("original_url") and obj.get("cover"):
                results.append(obj)
        if not results and keyword:
            params = {"query": keyword, "page": page}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            items = soup.select(".news-box .box, .result, .result-item, .news-item") or soup.find_all("div", class_=lambda c: c and ("result" in c or "news" in c))
            seen = set()
            for it in items:
                a = it.find("a")
                if not a:
                    continue
                href = (a.get("href") or "").strip()
                title = a.get_text(strip=True)
                if not href or not title:
                    continue
                if href in seen:
                    continue
                seen.add(href)
                original_url = href if href.startswith("http") else ("https://search.sohu.com/" + href.lstrip("/"))
                s = it.find("p") or it.find("div")
                summary = s.get_text(strip=True) if s else ""
                img = it.find("img")
                cover = (img.get("src") or "").strip() if img else ""
                if cover and not (cover.startswith("http://") or cover.startswith("https://")):
                    cover = "https://search.sohu.com/" + cover.lstrip("/")
                text = (title or "") + " " + (summary or "")
                if keyword and keyword not in text:
                    continue
                obj = {
                    "title": title,
                    "summary": summary,
                    "cover": cover,
                    "original_url": original_url,
                    "source": "搜狐新闻"
                }
                if obj.get("title") and obj.get("original_url") and obj.get("cover"):
                    results.append(obj)
        if not results:
            backup_url = "https://news.sohu.com/"
            try:
                resp = requests.get(backup_url, headers=headers, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, "html.parser")
                containers = []
                containers.extend(soup.find_all("li"))
                containers.extend(soup.find_all("article"))
                containers.extend(soup.find_all("div", class_=lambda c: c and ("news" in c or "item" in c or "list" in c or "pic" in c)))
                seen = set()
                for item in containers:
                    a = item.find("a")
                    if not a:
                        continue
                    href = (a.get("href") or "").strip()
                    title = a.get_text(strip=True)
                    if not href or not title:
                        continue
                    if href in seen:
                        continue
                    seen.add(href)
                    original_url = href if href.startswith("http") else ("https://news.sohu.com/" + href.lstrip("/"))
                    p = item.find("p") or item.find("div")
                    summary = p.get_text(strip=True) if p else ""
                    img = item.find("img")
                    cover = (img.get("src") or "").strip() if img else ""
                    if cover and not (cover.startswith("http://") or cover.startswith("https://")):
                        cover = "https://news.sohu.com/" + cover.lstrip("/")
                    text = (title or "") + " " + (summary or "")
                    if keyword and keyword not in text:
                        continue
                    obj = {
                        "title": title,
                        "summary": summary,
                        "cover": cover,
                        "original_url": original_url,
                        "source": "搜狐新闻"
                    }
                    if obj.get("title") and obj.get("original_url") and obj.get("cover"):
                        results.append(obj)
            except Exception:
                pass
    except Exception:
        pass
    if offset < 0:
        offset = 0
    if limit < 1:
        limit = 10
    return results[offset:offset+limit]

def crawl_xinhua_multi(keyword: str, offset: int = 0, limit: int = 10):
    bases = [
        "https://sc.news.cn/",
        "http://yn.news.cn/",
        "http://sx.news.cn/",
        "http://ha.news.cn/",
        "http://hq.news.cn/",
        "http://bj.news.cn/"
    ]
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    results = []
    seen = set()
    for base in bases:
        try:
            resp = requests.get(base, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            containers = []
            containers.extend(soup.find_all("li"))
            containers.extend(soup.find_all("article"))
            containers.extend(soup.find_all("div", class_=lambda c: c and ("news" in c or "item" in c or "list" in c or "pic" in c)))
            for item in containers:
                a = item.find("a")
                if not a:
                    continue
                href = (a.get("href") or "").strip()
                title = a.get_text(strip=True)
                if not href or not title:
                    continue
                if href in seen:
                    continue
                seen.add(href)
                if href.startswith("http"):
                    original_url = href
                else:
                    original_url = base.rstrip("/") + "/" + href.lstrip("/")
                p = item.find("p") or item.find("div")
                summary = p.get_text(strip=True) if p else ""
                img = item.find("img")
                cover = (img.get("src") or "").strip() if img else ""
                if cover and not (cover.startswith("http://") or cover.startswith("https://")):
                    cover = base.rstrip("/") + "/" + cover.lstrip("/")
                text = (title or "") + " " + (summary or "")
                if keyword and keyword not in text:
                    continue
                obj = {
                    "title": title,
                    "summary": summary,
                    "cover": cover,
                    "original_url": original_url,
                    "source": "新华网"
                }
                if obj.get("title") and obj.get("original_url") and obj.get("cover"):
                    results.append(obj)
        except Exception:
            pass
    if offset < 0:
        offset = 0
    if limit < 1:
        limit = 10
    return results[offset:offset+limit]
if __name__ == "__main__":
    import sys, json as _json
    kw = sys.argv[1] if len(sys.argv) > 1 else "宜宾"
    res = crawl_baidu_news(kw)
    print(_json.dumps(res, ensure_ascii=False, indent=2))
