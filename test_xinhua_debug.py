import requests
from bs4 import BeautifulSoup

import re

def test_crawl():
    url = "http://49.232.152.231:8000/getNews"
    print(f"Testing {url}")
    
    params = {
        "keyword": "成都",
        "curPage": 1,
        "sortField": 0,
        "searchFields": 1,
        "lang": "cn"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://so.news.cn/"
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        print(f"Headers: {resp.headers}")
        print(f"Content Type: {resp.headers.get('Content-Type')}")
        print(f"Text content: {resp.text[:1000]}")
        
        try:
            data = resp.json()
            print("JSON parse success")
            print(data)
        except Exception as e:
            print(f"JSON parse failed: {e}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_crawl()
