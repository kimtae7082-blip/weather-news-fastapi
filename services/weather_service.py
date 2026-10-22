import os
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from database.connection import query, execute

REGION_COORDINATES = {
    'seoul': (37.5665, 126.9780, '서울'),
    'busan': (35.1796, 129.0756, '부산'),
    'daegu': (35.8714, 128.6014, '대구'),
    'incheon': (37.4563, 126.7052, '인천'),
    'gwangju': (35.1595, 126.8526, '광주'),
    'daejeon': (36.3504, 127.3845, '대전'),
    'ulsan': (35.5384, 129.3114, '울산'),
    'sejong': (36.4800, 127.2890, '세종'),
    'gyeonggi': (37.4138, 127.5183, '경기'),
    'gangwon': (37.8228, 128.1555, '강원'),
    'chungbuk': (36.8000, 127.7000, '충북'),
    'chungnam': (36.5184, 126.8000, '충남'),
    'jeonbuk': (35.8203, 127.1089, '전북'),
    'jeonnam': (34.8679, 126.9910, '전남'),
    'gyeongbuk': (36.4919, 128.8889, '경북'),
    'gyeongnam': (35.4606, 128.2132, '경남'),
    'jeju': (33.4996, 126.5312, '제주'),
}

WEATHER_MAP = {
    200: '약한 천둥번개',
    201: '천둥번개',
    202: '강한 천둥번개',
    210: '약한 천둥번개',
    211: '천둥번개',
    212: '강한 천둥번개',
    221: '불규칙한 천둥번개',
    230: '약한 천둥번개와 이슬비',
    231: '천둥번개와 이슬비',
    232: '강한 천둥번개와 이슬비',
    300: '약한 이슬비',
    301: '이슬비',
    302: '강한 이슬비',
    310: '약한 이슬비',
    311: '이슬비',
    312: '강한 이슬비',
    313: '소나기성 이슬비',
    314: '강한 소나기성 이슬비',
    321: '소나기성 이슬비',
    500: '약한 비',
    501: '비',
    502: '강한 비',
    503: '매우 강한 비',
    504: '극심한 비',
    511: '어는 비',
    520: '약한 소나기',
    521: '소나기',
    522: '강한 소나기',
    531: '불규칙한 소나기',
    600: '약한 눈',
    601: '눈',
    602: '강한 눈',
    611: '진눈깨비',
    612: '약한 소나기성 진눈깨비',
    613: '소나기성 진눈깨비',
    615: '약한 비와 눈',
    616: '비와 눈',
    620: '약한 소나기성 눈',
    621: '소나기성 눈',
    622: '강한 소나기성 눈',
    701: '안개',
    711: '연기',
    721: '연무',
    731: '모래먼지',
    741: '안개',
    751: '모래',
    761: '먼지',
    762: '화산재',
    771: '돌풍',
    781: '토네이도',
    800: '맑음',
    801: '구름 조금',
    802: '부분적으로 흐림',
    803: '구름 많음',
    804: '흐림',
}

def weather_code_to_text(code):
    return WEATHER_MAP.get(int(code), '알 수 없음')

def get_all_regions():
    return query('SELECT region_id, city_code, region_name FROM region ORDER BY region_id')

def get_latest_observations():
    rows = query("""
        SELECT o.observation_id, r.region_id, r.region_name, r.city_code,
               o.temperature, o.humidity, o.wind_speed, o.precipitation,
               o.weather_code, o.observed_at
        FROM weather_observation o
        JOIN region r ON o.region_id = r.region_id
        JOIN (SELECT region_id, MAX(observed_at) AS latest_time
              FROM weather_observation GROUP BY region_id) latest
          ON o.region_id = latest.region_id AND o.observed_at = latest.latest_time
        ORDER BY r.region_id
    """)
    for row in rows:
        row['weather_status'] = weather_code_to_text(row['weather_code'])
    return rows

def fetch_and_save_weather_data():
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        raise ValueError('OPENWEATHER_API_KEY를 .env에 설정하세요.')
    counts = {'insertedCount': 0, 'skippedCount': 0, 'failedCount': 0}
    with httpx.Client(timeout=20) as client:
        for region in get_all_regions():
            coordinate = REGION_COORDINATES.get(region['city_code'])
            if not coordinate:
                counts['failedCount'] += 1
                continue
            lat, lon, _ = coordinate
            try:
                response = client.get('https://api.openweathermap.org/data/2.5/weather', params={
                    'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'metric', 'lang': 'kr'
                })
                response.raise_for_status()
                data = response.json()
                code = int(data.get('weather', [{'id': 0}])[0]['id'])
                rain = float((data.get('rain') or {}).get('1h') or 0)
                snow = float((data.get('snow') or {}).get('1h') or 0)
                observed = datetime.fromtimestamp(data['dt'], ZoneInfo('Asia/Seoul')).replace(tzinfo=None)
                result = execute("""
                    INSERT INTO weather_observation
                      (region_id, temperature, humidity, wind_speed, precipitation, weather_code, observed_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                      temperature=VALUES(temperature), humidity=VALUES(humidity),
                      wind_speed=VALUES(wind_speed), precipitation=VALUES(precipitation),
                      weather_code=VALUES(weather_code)
                """, (region['region_id'], data['main']['temp'], data['main']['humidity'],
                          (data.get('wind') or {}).get('speed', 0), rain + snow, code, observed))
                counts['insertedCount' if result['affected'] == 1 else 'skippedCount'] += 1
            except Exception as exc:
                print(f"{region['region_name']} 날씨 수집 실패: {exc}")
                counts['failedCount'] += 1
    return counts

def evaluate_weather_events(observation):
    events = []
    temp = float(observation['temperature'])
    rain = float(observation.get('precipitation') or 0)
    wind = float(observation['wind_speed'])
    code = int(observation['weather_code'])
    name = observation['region_name']
    def add(event_type, level, description):
        events.append(dict(event_type=event_type, severity_level=level, description=description))
    if temp >= 33: add('폭염', '경보' if temp >= 35 else '주의', f'{name}의 현재 기온이 {temp}℃로 높습니다.')
    if temp <= -12: add('한파', '경보' if temp <= -15 else '주의', f'{name}의 현재 기온이 {temp}℃로 매우 낮습니다.')
    if rain >= 30: add('호우', '경보' if rain >= 50 else '주의', f'{name}에서 {rain}mm의 강수가 관측되었습니다.')
    if wind >= 14: add('강풍', '경보' if wind >= 21 else '주의', f'{name}의 풍속이 {wind}m/s로 강합니다.')
    if 600 <= code <= 622: add('대설', '주의', f'{name}에 눈이 관측되고 있습니다.')
    if 200 <= code <= 232: add('뇌우', '주의', f'{name}에서 뇌우가 관측되고 있습니다.')
    return events

def analyze_and_save_events():
    observations = get_latest_observations()
    saved = 0
    for obs in observations:
        for event in evaluate_weather_events(obs):
            result = execute("""
                INSERT INTO weather_event (observation_id,region_id,event_type,severity_level,description)
                VALUES (%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE severity_level=VALUES(severity_level), description=VALUES(description)
            """, (obs['observation_id'],obs['region_id'],event['event_type'],
                      event['severity_level'],event['description']))
            if result['affected'] > 0: saved += 1
    return {'analyzedCount': len(observations), 'savedEventCount': saved}

def get_latest_events():
    return query("""
        SELECT e.event_id,e.region_id,r.region_name,e.event_type,e.severity_level,
               e.description,e.created_at
        FROM weather_event e JOIN region r ON e.region_id=r.region_id
        ORDER BY e.created_at DESC LIMIT 50
    """)

def create_news(region, temp, weather_status, warning_type='없음'):
    row = query('SELECT region_id FROM region WHERE region_name=%s LIMIT 1', (region,), one=True)
    if not row: raise ValueError(f'존재하지 않는 지역입니다: {region}')
    warning_type = warning_type or '없음'
    title = f'[{region}] 현재 날씨 {float(temp):.1f}℃ · {weather_status}'
    content = f'{region} 지역은 현재 {temp}℃이며 {weather_status} 날씨가 나타나고 있습니다.'
    if warning_type != '없음':
        content += f' 현재 {warning_type} 관련 기상 상황에 주의가 필요합니다.'
    result = execute("""
        INSERT INTO weather_news (region_id,temp,weather_status,warning_type,news_title,news_content)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (row['region_id'],temp,weather_status,warning_type,title,content))
    return query("""
        SELECT n.id,r.region_name AS region,n.temp,n.weather_status,n.warning_type,
               n.news_title,n.news_content,n.created_at
        FROM weather_news n JOIN region r ON n.region_id=r.region_id WHERE n.id=%s
    """, (result['last_id'],), one=True)

def get_all_news():
    return query("""
        SELECT n.id,r.region_name AS region,n.temp,n.weather_status,n.warning_type,
               n.news_title,n.news_content,n.created_at
        FROM weather_news n JOIN region r ON n.region_id=r.region_id
        ORDER BY n.created_at DESC LIMIT 30
    """)

def generate_news_article():
    created = []
    for obs in get_latest_observations():
        warning = ', '.join(x['event_type'] for x in evaluate_weather_events(obs)) or '없음'
        created.append(create_news(obs['region_name'], obs['temperature'], obs['weather_status'], warning))
    return created
