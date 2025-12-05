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

def crawl_xinhua_news(keyword: str, page: int = 1):
    url = f"https://so.news.cn/#search/0/{keyword}/{page}/0"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "no-cache",
        "connection": "keep-alive",
        "host": "so.news.cn",
        "pragma": "no-cache",
        "referer": "https://so.news.cn/",
        "sec-ch-ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
    }
    results = []
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Try common containers
        containers = []
        for cls in ["result", "news", "list", "search-result", "item"]:
            containers.extend(soup.find_all(class_=lambda c: c and cls in c))
        if not containers:
            containers = soup.find_all("article") or soup.find_all("li")
        for item in containers:
            obj = {}
            try:
                a_tag = item.find("a")
                if a_tag:
                    obj["title"] = a_tag.get_text(strip=True)
                    obj["original_url"] = a_tag.get("href", "")
                # summary
                p_tag = item.find("p") or item.find("div")
                if p_tag:
                    obj["summary"] = p_tag.get_text(strip=True)
                # cover
                img_tag = item.find("img")
                if img_tag:
                    obj["cover"] = img_tag.get("src", "")
                obj["source"] = "新华网"
                if obj.get("title") and obj.get("original_url") and obj.get("cover"):
                    results.append(obj)
            except Exception:
                pass
    except Exception:
        pass
    return results

if __name__ == "__main__":
    import sys, json as _json
    kw = sys.argv[1] if len(sys.argv) > 1 else "宜宾"
    res = crawl_baidu_news(kw)
    print(_json.dumps(res, ensure_ascii=False, indent=2))
