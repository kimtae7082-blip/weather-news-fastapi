import httpx
from database.connection import query

def get_climate_analysis(region_id):
    region = query('SELECT region_id,region_name,latitude,longitude FROM region WHERE region_id=%s', (region_id,), one=True)
    if not region: raise ValueError('지역을 찾을 수 없습니다.')
    response = httpx.get('https://archive-api.open-meteo.com/v1/archive', params={
        'latitude': str(region['latitude']), 'longitude': str(region['longitude']),
        'start_date': '2016-01-01', 'end_date': '2025-12-31',
        'daily': 'temperature_2m_mean,temperature_2m_max,precipitation_sum',
        'timezone': 'Asia/Seoul'
    }, timeout=90)
    response.raise_for_status()
    daily = response.json().get('daily') or {}
    dates = daily.get('time')
    if not isinstance(dates, list) or not dates: raise ValueError('기후 데이터가 없습니다.')
    annual = {}
    for i, date in enumerate(dates):
        year = int(date[:4])
        item = annual.setdefault(year, {'year': year, 'temp_sum': 0, 'temp_count': 0, 'rainfall': 0, 'heatwaveDays': 0})
        temp = daily['temperature_2m_mean'][i]
        maximum = daily['temperature_2m_max'][i]
        rain = daily['precipitation_sum'][i]
        if temp is not None: item['temp_sum'] += temp; item['temp_count'] += 1
        if rain is not None: item['rainfall'] += rain
        if maximum is not None and maximum >= 33: item['heatwaveDays'] += 1
    years = [dict(year=item['year'], avgTemperature=round(item['temp_sum']/item['temp_count'], 2) if item['temp_count'] else None,
                  rainfall=round(item['rainfall'], 1), heatwaveDays=item['heatwaveDays']) for item in annual.values()]
    first, last = years[0], years[-1]
    temp_diff = round(last['avgTemperature']-first['avgTemperature'], 2) if first['avgTemperature'] is not None and last['avgTemperature'] is not None else None
    return {'region': region['region_name'], 'period': '2016~2025', 'years': years,
            'comparison': {'temperatureDifference': temp_diff,
                           'rainfallDifference': round(last['rainfall']-first['rainfall'], 1),
                           'heatwaveDaysDifference': last['heatwaveDays']-first['heatwaveDays']}}
