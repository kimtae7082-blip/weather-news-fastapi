# Open-Meteo 과거 일별 자료를 연도별 통계로 바꿉니다. 현재 관측 DB와는 별도 자료입니다.
from collections import defaultdict
import httpx
from services.regions import regions,COORDS

# DB의 지역 번호로 대표 좌표를 찾습니다. 없는 지역은 API에서 404로 안내합니다.
async def analyze_climate(region_id):
    region=next((r for r in regions() if r['region_id']==region_id),None)
    if not region:raise ValueError('지역을 찾을 수 없습니다.')
    lat,lon=COORDS[region['city_code']]
    # 조회 기간은 2016~2025년으로 고정되어 있습니다. 자동으로 최신 연도로 바뀌지 않습니다.
    async with httpx.AsyncClient(timeout=90) as client:
        response=await client.get('https://archive-api.open-meteo.com/v1/archive',params={'latitude':lat,'longitude':lon,'start_date':'2016-01-01','end_date':'2025-12-31','daily':'temperature_2m_mean,temperature_2m_max,precipitation_sum','timezone':'Asia/Seoul'})
        response.raise_for_status(); d=response.json()['daily']
    # 연도별로 기온 합계·유효 일수·강수 합계·고온 일수를 모읍니다.
    annual=defaultdict(lambda:{'tempSum':0,'tempCount':0,'rainfall':0,'heatwaveDays':0})
    for i,date in enumerate(d['time']):
        a=annual[int(date[:4])];t=d['temperature_2m_mean'][i];mx=d['temperature_2m_max'][i];rain=d['precipitation_sum'][i]
        # 빠진 기온을 0으로 채우면 평균이 낮아지므로 유효한 날만 분모에 넣습니다.
        if t is not None:a['tempSum']+=t;a['tempCount']+=1
        if rain is not None:a['rainfall']+=rain
        # 여기서 폭염일수는 최고기온 33℃ 이상인 날의 수라는 자체 집계 정의입니다.
        if mx is not None and mx>=33:a['heatwaveDays']+=1
    years=[{'year':y,'avgTemperature':round(a['tempSum']/a['tempCount'],2) if a['tempCount'] else None,'rainfall':round(a['rainfall'],1),'heatwaveDays':a['heatwaveDays']} for y,a in sorted(annual.items())]
    # 첫해와 마지막 해의 차이입니다. 10년 전체의 추세나 원인을 검정한 값은 아닙니다.
    # 현재 구현은 daily에 최소 한 해의 자료가 있다는 전제를 사용합니다.
    first,last=years[0],years[-1]
    return {'region':region['region_name'],'period':'2016~2025','years':years,'comparison':{'temperatureDifference':round(last['avgTemperature']-first['avgTemperature'],2) if first['avgTemperature'] is not None and last['avgTemperature'] is not None else None,'rainfallDifference':round(last['rainfall']-first['rainfall'],1),'heatwaveDaysDifference':last['heatwaveDays']-first['heatwaveDays']}}

