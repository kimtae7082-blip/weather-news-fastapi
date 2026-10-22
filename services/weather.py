# OpenWeather 현재 날씨 수집 → 관측 저장 → 자체 이벤트 분석을 담당합니다.
import os
from datetime import datetime, timezone
import httpx
from database.connection import db, query
from services.regions import regions, COORDS

# 공급자의 날씨 코드를 화면용 한국어로 바꿉니다. 알 수 없는 코드는 정보 없음입니다.
def status(code):
    code=int(code or 0)
    if 200<=code<300:return '뇌우'
    if 300<=code<400:return '이슬비'
    if 500<=code<600:return '비'
    if 600<=code<700:return '눈'
    if 700<=code<800:return '안개/대기현상'
    return {800:'맑음',801:'구름 조금',802:'구름 많음',803:'흐림',804:'매우 흐림'}.get(code,'정보 없음')

# 지역마다 관측 시각이 가장 큰(가장 최근인) 행을 선택하고 날씨 이름을 붙입니다.
# observed_at은 수집 코드에서 UTC 문자열로 저장하므로 한국 시각과 구분해야 합니다.
def observations():
    rows=query("""SELECT o.observation_id,r.region_id,r.region_name,r.city_code,o.temperature,o.humidity,o.wind_speed,o.precipitation,o.weather_code,o.observed_at FROM weather_observation o JOIN region r ON r.region_id=o.region_id JOIN (SELECT region_id,MAX(observed_at) t FROM weather_observation GROUP BY region_id) x ON x.region_id=o.region_id AND x.t=o.observed_at ORDER BY r.region_id""")
    for r in rows:r['weather_status']=status(r['weather_code'])
    return rows

# 한 번 호출할 때 DB의 지역을 순서대로 조회합니다. 자동 정기 수집 기능은 없습니다.
async def collect():
    # 실제 키는 환경 변수에서만 읽습니다. 예시 문자열은 사용할 수 없습니다.
    key=os.getenv('OPENWEATHER_API_KEY')
    if not key or key=='YOUR_OPENWEATHER_KEY':raise ValueError('OPENWEATHER_API_KEY를 .env에 입력하세요.')
    # 지역 하나가 실패해도 나머지는 계속 수집하며 errors에 실패 이유를 남깁니다.
    results={'insertedCount':0,'skippedCount':0,'failedCount':0,'errors':[]}
    async with httpx.AsyncClient(timeout=20) as client:
        for r in regions():
            try:
                lat,lon=COORDS[r['city_code']]
                resp=await client.get('https://api.openweathermap.org/data/2.5/weather',params={'lat':lat,'lon':lon,'appid':key,'units':'metric','lang':'kr'})
                resp.raise_for_status(); j=resp.json()
                # UNIX 시각을 UTC로 변환합니다. 시간대 표시는 DB 문자열에 남지 않습니다.
                observed=datetime.fromtimestamp(j['dt'],timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                # API가 비·눈 항목을 생략하면 0으로 처리합니다.
                # 여기서는 최근 1시간 비와 눈의 값을 합쳐 precipitation에 넣습니다.
                rain=float(j.get('rain',{}).get('1h',0))+float(j.get('snow',{}).get('1h',0))
                with db() as conn:
                    with conn.cursor() as cur:
                        # m/s × 3.6 = km/h. DB와 화면의 풍속 단위를 맞춥니다.
                        # 중복 키가 있으면 기존 관측값을 갱신합니다. 중복 판단은 DB 제약조건에 달려 있습니다.
                        cur.execute("""INSERT INTO weather_observation(region_id,temperature,humidity,wind_speed,precipitation,weather_code,observed_at) VALUES(%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE temperature=VALUES(temperature),humidity=VALUES(humidity),wind_speed=VALUES(wind_speed),precipitation=VALUES(precipitation),weather_code=VALUES(weather_code)""",(r['region_id'],j['main']['temp'],j['main']['humidity'],j['wind']['speed']*3.6,rain,j['weather'][0]['id'],observed))
                        # rowcount==1만 신규 삽입으로 셉니다.
                        # skippedCount에는 실제 갱신된 행도 포함될 수 있으므로 '미수집 수'가 아닙니다.
                        results['insertedCount' if cur.rowcount==1 else 'skippedCount']+=1
            except Exception as exc:
                results['failedCount']+=1;results['errors'].append(f"{r['region_name']}: {exc}")
    return results

# 학습용 임계값입니다. 공식 기상청 특보 기준으로 인용하면 안 됩니다.
# 풍속은 DB의 km/h를 사용합니다. 여러 조건을 만족하면 이벤트도 여러 개 나옵니다.
def event_rules(o):
    t=float(o['temperature']); w=float(o['wind_speed']);rain=float(o['precipitation'] or 0);code=int(o['weather_code']); found=[]
    if t>=33:found.append(('폭염','경보' if t>=35 else '주의',f'기온 {t}℃'))
    if t<=-12:found.append(('한파','경보' if t<=-15 else '주의',f'기온 {t}℃'))
    if rain>=30:found.append(('호우','경보' if rain>=50 else '주의',f'강수량 {rain}mm'))
    if w>=14:found.append(('강풍','경보' if w>=21 else '주의',f'풍속 {w}km/h'))
    if 600<=code<700:found.append(('대설','주의','눈 날씨 코드 감지'))
    if 200<=code<300:found.append(('뇌우','주의','뇌우 날씨 코드 감지'))
    return found

# 최신 관측마다 규칙을 적용하고 한 연결에서 이벤트를 저장합니다.
# 기존 이벤트를 삭제하지 않으므로 현재 조건에서 벗어난 과거 이벤트도 남습니다.
def analyze():
    obs=observations(); count=0
    with db() as conn:
        with conn.cursor() as cur:
            for o in obs:
                for name,level,desc in event_rules(o):
                    cur.execute("""INSERT INTO weather_event(observation_id,region_id,event_type,severity_level,description) VALUES(%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE severity_level=VALUES(severity_level),description=VALUES(description)""",(o['observation_id'],o['region_id'],name,level,desc));count+=1
    return {'analyzedCount':len(obs),'savedEventCount':count}

# 최근 생성된 이벤트 최대 50건입니다. 현재 유효한 공식 특보 목록이 아닙니다.
def events():
    return query("""SELECT e.event_id,e.region_id,r.region_name,e.event_type,e.severity_level,e.description,e.created_at FROM weather_event e JOIN region r ON r.region_id=e.region_id ORDER BY e.created_at DESC LIMIT 50""")

