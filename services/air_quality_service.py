from concurrent.futures import ThreadPoolExecutor
import httpx
from database.connection import query

def grade(value, pollutant):
    if value is None: return '정보 없음'
    limits = (30, 80, 150) if pollutant == 'pm10' else (15, 35, 75)
    return '좋음' if value <= limits[0] else '보통' if value <= limits[1] else '나쁨' if value <= limits[2] else '매우 나쁨'

def fetch_air_quality():
    regions = query('SELECT region_id,region_name,latitude,longitude FROM region ORDER BY region_id')
    def fetch(region):
        base = {'region_id': region['region_id'], 'region_name': region['region_name']}
        try:
            response = httpx.get('https://air-quality-api.open-meteo.com/v1/air-quality', params={
                'latitude': str(region['latitude']), 'longitude': str(region['longitude']),
                'current': 'pm10,pm2_5', 'timezone': 'Asia/Seoul'
            }, timeout=25)
            response.raise_for_status()
            current = response.json()['current']
            pm10, pm25 = current.get('pm10'), current.get('pm2_5')
            return {**base, 'pm10': pm10, 'pm25': pm25,
                    'pm10_grade': grade(pm10, 'pm10'), 'pm25_grade': grade(pm25, 'pm25'),
                    'observed_at': current.get('time')}
        except Exception as exc:
            return {**base, 'error': str(exc)}
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(fetch, regions))
