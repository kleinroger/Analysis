import requests
from bs4 import BeautifulSoup, Comment
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def crawl_baidu_news(keyword):
    """
    Crawls Baidu News for the given keyword.
    Returns a list of dictionaries with keys: title, summary, cover, original_url, source, date.
    """
    url = "https://www.baidu.com/s"
    params = {
        "rtt": "1",
        "bsst": "1",
        "cl": "2",
        "tn": "news",
        "rsv_dl": "ns_pc",
        "word": keyword
    }
    
    # Headers from probe script
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "no-cache",
        "connection": "keep-alive",
        "cookie": "ORIGIN=0; bdime=0; BDUSS=lXV0RnY3RSY1ZVfi1mQ3lLZ0FFNU5GVDZWbzUyek5oQzJKSG9GZUpTS1VSREJvSVFBQUFBJCQAAAAAAQAAAAEAAAAKAakOsru-9WJ1anVlbGoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJS3CGiUtwhob1; PSTM=1764816623; BD_UPN=12314753; BIDUPSID=A29BFC946D0D17CF52697FF6CBDCEF08; BDORZ=FFFB88E999055A3F8A630C64834BD6D0; sug=3; sugstore=0; H_PS_645EC=0a72NDDj6cHIl8eMo8XLBnEGf8DtzWhQXj0lArmkrl9J5W4gRTtlHiSY2uTcACH2rQKAIgo; BDUSS_BFESS=lXV0RnY3RSY1ZVfi1mQ3lLZ0FFNU5GVDZWbzUyek5oQzJKSG9GZUpTS1VSREJvSVFBQUFBJCQAAAAAAQAAAAEAAAAKAakOsru-9WJ1anVlbGoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJS3CGiUtwhob1; BAIDUID=DFC91FFEFCC05ACF1B358570B83C3FCC:FG=1; H_WISE_SIDS=66101_66109_66189_66233_66203_66285_66259_66393_66464_66515_66529_66550_66584_66578_66593_66615_66654_66664_66672_66666_66697_66718_66744_66771_66787_66792_66800_66803_66599; BAIDUID_BFESS=DFC91FFEFCC05ACF1B358570B83C3FCC:FG=1; BA_HECTOR=a5ala585ak0g852l00802l0g242h801kj1tqg25; ZFY=nTmFFohdGanMF985RwXkiAH2ZbpNtVOe1U:ASc7zlIGk:C; BDRCVFR[C0p6oIjvx-c]=mbxnW11j9Dfmh7GuZR8mvqV; H_PS_PSSID=60279_63144_64005_65312_66103_66107_66215_66192_66201_66163_66282_66253_66393_66516_66529_66546_66585_66578_66592_66600_66641_66653_66682_66674_66670_66689_66720_66743_66792_66804_66599; delPer=0; BD_CK_SAM=1; PSINO=1; arialoadData=false; BDSVRTM=570",
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

    results_data = []
    
    try:
        logger.info(f"Crawling Baidu News for keyword: {keyword}")
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        containers = soup.find_all('div', class_='c-container')
        
        if not containers:
             # Try finding 'result-op' if 'c-container' not found (though usually they co-exist)
             containers = soup.find_all('div', class_='result-op')

        logger.info(f"Found {len(containers)} result containers")

        for item in containers:
            news_item = {}
            
            # Strategy 1: Extract from s-data comment (Most reliable for Baidu)
            comment = item.find(string=lambda text: isinstance(text, Comment) and "s-data:" in text)
            if comment:
                try:
                    data_str = comment.strip().replace("s-data:", "", 1)
                    data = json.loads(data_str)
                    
                    news_item['title'] = data.get('title', '').replace('<em>', '').replace('</em>', '')
                    news_item['summary'] = data.get('summary', '').replace('<em>', '').replace('</em>', '')
                    news_item['cover'] = data.get('leftImgSrc', '')
                    news_item['original_url'] = data.get('titleUrl', '')
                    news_item['source'] = data.get('sourceName', '')
                    news_item['date'] = data.get('dispTime', '')
                    
                    results_data.append(news_item)
                    continue
                except Exception as e:
                    logger.warning(f"Error parsing s-data comment: {e}")
            
            # Strategy 2: Fallback to HTML parsing
            try:
                title_tag = item.find('h3')
                if title_tag:
                    news_item['title'] = title_tag.get_text(strip=True)
                    a_tag = title_tag.find('a')
                    if a_tag:
                        news_item['original_url'] = a_tag.get('href', '')
                
                summary_div = item.find('div', class_='c-summary')
                if summary_div:
                     news_item['summary'] = summary_div.get_text(strip=True)
                
                # Try to find image
                img_tag = item.find('img')
                if img_tag:
                    news_item['cover'] = img_tag.get('src', '')
                
                # Try to find source
                source_div = item.find('div', class_='c-author') or item.find('span', class_='c-color-gray')
                if source_div:
                     news_item['source'] = source_div.get_text(strip=True)
                
                if news_item.get('title'):
                    results_data.append(news_item)
            except Exception as e:
                logger.warning(f"Error parsing HTML fallback: {e}")

    except Exception as e:
        logger.error(f"Error during crawling: {e}")
        
    return results_data

if __name__ == "__main__":
    # Test locally
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else "宜宾"
    res = crawl_baidu_news(kw)
    print(json.dumps(res, ensure_ascii=False, indent=2))
