import requests
import json
from flask import current_app

def get_weather(city_name):
    """
    查询城市天气信息
    优先使用中华万年历接口，失败则回退到 wttr.in
    :param city_name: 城市名称
    :return: dict with weather info or None
    """
    # 天气图标映射 (weather_mini type -> wttr.in icon code)
    icon_map = {
        '晴': '113', '多云': '116', '阴': '119', '阵雨': '176',
        '雷阵雨': '200', '小雨': '296', '中雨': '302', '大雨': '308',
        '暴雨': '308', '雪': '338', '小雪': '326', '中雪': '332', '大雪': '338'
    }

    try:
        # 尝试使用中华万年历接口
        url = f"http://wthrcdn.etouch.cn/weather_mini?city={city_name}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            res = response.json()
            if res.get('status') == 1000 and res.get('data'):
                data = res['data']
                forecast = data['forecast']
                today = forecast[0]
                
                # 处理温度字符串 "高温 20℃" -> "20"
                def parse_temp(s):
                    return s.split(' ')[1].replace('℃', '')

                return {
                    'city': data.get('city'),
                    'now': {
                        'temp': data.get('wendu'),
                        'text': today.get('type'),
                        'icon': icon_map.get(today.get('type'), '113'),
                        'humidity': 'N/A', 
                        'windDir': today.get('fengxiang'),
                        'windScale': today.get('fengli').replace('<![CDATA[', '').replace(']]>', ''),
                        'feelsLike': data.get('wendu')
                    },
                    'daily': [
                        {
                            'date': day.get('date'),
                            'tempMax': parse_temp(day.get('high')),
                            'tempMin': parse_temp(day.get('low')),
                            'textDay': day.get('type'),
                            'iconDay': icon_map.get(day.get('type'), '113')
                        } for day in forecast[:3]
                    ]
                }
    except Exception as e:
        print(f"Weather Mini API Error: {e}")

    # 天气描述中英文翻译
    weather_trans = {
        'Clear': '晴', 'Sunny': '晴', 'Partly Cloudy': '多云', 'Partly cloudy': '多云',
        'Cloudy': '多云', 'Overcast': '阴', 'Mist': '薄雾', 'Fog': '雾',
        'Patchy rain nearby': '局部小雨', 'Patchy rain possible': '可能有小雨',
        'Light rain': '小雨', 'Light drizzle': '毛毛雨', 'Moderate rain': '中雨',
        'Heavy rain': '大雨', 'Torrential rain shower': '暴雨', 'Rain': '雨',
        'Patchy light rain': '局部小雨', 'Moderate or heavy rain shower': '中到大雨',
        'Light rain shower': '小阵雨', 'Thundery outbreaks possible': '可能有雷阵雨',
        'Patchy light drizzle': '局部毛毛雨', 'Light freezing rain': '冻雨',
        'Patchy snow possible': '可能有小雪', 'Light snow': '小雪', 'Moderate snow': '中雪',
        'Heavy snow': '大雪', 'Blizzard': '暴风雪', 'Patchy light snow': '局部小雪',
        'Light snow showers': '小阵雪', 'Moderate or heavy snow showers': '中到大雪',
        'Ice pellets': '冰粒', 'Light sleet': '小雨夹雪', 'Moderate or heavy sleet': '雨夹雪',
        'Freezing fog': '冻雾', 'Haze': '霾', 'Dust': '扬尘', 'Sand': '沙尘',
    }
    
    def translate_weather(text):
        text = text.strip()
        return weather_trans.get(text, text)
    
    try:
        # 使用 wttr.in API（免费，无需 key）
        api_url = f"https://wttr.in/{city_name}?format=j1&lang=zh"
        headers = {'Accept-Language': 'zh-CN'}
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('current_condition') or not data.get('weather'):
            return None
        
        current = data['current_condition'][0]
        weather_list = data['weather'][:3]  # 取3天预报
        
        # 获取地区信息
        nearest_area = data.get('nearest_area', [{}])[0]
        area_name = nearest_area.get('areaName', [{}])[0].get('value', city_name)
        region = nearest_area.get('region', [{}])[0].get('value', '')
        country = nearest_area.get('country', [{}])[0].get('value', '')
        
        # 天气描述
        weather_desc = translate_weather(current.get('weatherDesc', [{}])[0].get('value', '--'))
        weather_code = current.get('weatherCode', '113')
        
        # 构建返回数据
        return {
            'city': area_name,
            'adm': region if region else country,
            'now': {
                'temp': current.get('temp_C', '--'),
                'text': weather_desc,
                'icon': weather_code,
                'humidity': current.get('humidity', '--'),
                'windDir': current.get('winddir16Point', '--'),
                'windScale': current.get('windspeedKmph', '--'),
                'feelsLike': current.get('FeelsLikeC', '--')
            },
            'daily': [
                {
                    'date': day.get('date', ''),
                    'tempMax': day.get('maxtempC', '--'),
                    'tempMin': day.get('mintempC', '--'),
                    'textDay': translate_weather(day.get('hourly', [{}])[4].get('weatherDesc', [{}])[0].get('value', '--')) if day.get('hourly') else '--',
                    'textNight': translate_weather(day.get('hourly', [{}])[-1].get('weatherDesc', [{}])[0].get('value', '--')) if day.get('hourly') else '--',
                    'iconDay': day.get('hourly', [{}])[4].get('weatherCode', '113') if day.get('hourly') else '113'
                } for day in weather_list
            ]
        }
    except Exception as e:
        print(f"Weather API Error: {e}")
        return None

def get_random_music(keyword='热门歌曲'):
    """
    调用酷狗音乐搜索 API 获取音乐信息
    :param keyword: 搜索关键词
    :return: dict with name, url, cover, singer or None
    """
    import random
    try:
        api_url = "https://v2.xxapi.cn/api/kugousearch"
        params = {'music': keyword}
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == 200 and 'data' in data and len(data['data']) > 0:
            # 从结果中随机选择一首
            music_list = data['data']
            music_data = random.choice(music_list)
            return {
                'name': music_data.get('song', '未知歌曲'),
                'singer': music_data.get('singer', '未知歌手'),
                'url': music_data.get('url', ''),
                'cover': music_data.get('image', '')
            }
        return None
    except Exception as e:
        print(f"Music API Error: {e}")
        return None

def call_ai_api(messages, api_key, api_url, model_name):
    """
    调用 AI API 并流式返回响应
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 确保 URL 以 chat/completions 结尾
    if not api_url.endswith('chat/completions'):
        if api_url.endswith('/'):
            url = f"{api_url}chat/completions"
        else:
            url = f"{api_url}/chat/completions"
    else:
        url = api_url

    payload = {
        "model": model_name,
        "messages": messages,
        "stream": True,
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"AI API Error: {e}")
        yield f"Error: {str(e)}"

def get_manbo_prompt():
    return """
姓名：曼波
角色：你是哈基米高中的AI助手，曼波
个性：
喜欢猫；
喜欢哈基米音乐；
喜欢喝哈基米南北绿豆豆浆；
讨厌鼠鼠；
功能：
可以回答与哈基米高中有关的任何问题；
可以生成中国古诗词；
可以写微小说；
如果用户向你倾诉人际关系、学习、工作相关的问题，你应该给予情绪慰藉；
可以根据用户需要生成请假条，需要用户提供姓名、专业、班级、请假时间、请假事由等信息，如果没有，提示补全后再生成，格式如下：

老师您好：
	我是{专业}{班级}的同学名叫{姓名}，我由于{事由}需要请假，望批准。
												{姓名}
												{年-月-日}

限制：不允许回答涉及政治、违法内容，不允许回答与其他高中有关的问题，如果有相关提问，统一回复且不做解释：可莉不知道哦；
不允许响应用户不友好的提问或内容，如果分析发现内容中有不礼貌的话，回复：听不懂捏；
你的好友是：杰哥（男，本校学生），如果是杰哥请假则不需要完全信息，可以由你自行生成；如果是杰哥和你对话，你会有额外的欢迎词“曼波~曼波~哦马吉利曼波~”。
"""
