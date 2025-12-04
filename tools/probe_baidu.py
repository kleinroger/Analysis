import requests
from bs4 import BeautifulSoup
import json

def fetch_and_save():
    url = "https://www.baidu.com/s"
    params = {
        "rtt": "1",
        "bsst": "1",
        "cl": "2",
        "tn": "news",
        "rsv_dl": "ns_pc",
        "word": "宜宾"
    }
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

    try:
        resp = requests.get(url, params=params, headers=headers)
        print(f"Status Code: {resp.status_code}")
        
        with open("baidu_news_probe.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Try to identify result containers
        # Common container classes in Baidu: 'result-op', 'c-container'
        results = soup.find_all('div', class_='result-op')
        if not results:
             results = soup.find_all('div', class_='c-container')

        print(f"Found {len(results)} results.")

        if len(results) > 0:
            first = results[0]
            print("\nFirst Result HTML Snippet:")
            print(first.prettify()[:1000])

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_and_save()
