# 관측값을 정해진 문장 틀에 넣어 뉴스 초안을 저장합니다. 생성형 AI 호출은 없습니다.
from database.connection import db,query
from services.weather import observations,status

# 최신 생성 순으로 최대 30건을 읽고 지역 이름을 연결합니다.
def list_news():
    return query("""SELECT n.id,r.region_name AS region,n.temp,n.weather_status,n.warning_type,n.news_title,n.news_content,n.created_at FROM weather_news n JOIN region r ON r.region_id=n.region_id ORDER BY n.created_at DESC LIMIT 30""")

# 지역 이름 또는 city_code를 허용합니다. 없는 지역은 저장 전에 거절합니다.
def create(region,temp,weather_status,warning_type='없음'):
    found=query('SELECT region_id FROM region WHERE region_name=%s OR city_code=%s LIMIT 1',(region,region))
    if not found:raise ValueError('등록되지 않은 지역입니다.')
    # 입력된 값을 그대로 문장화합니다. 사실 확인·공식 특보 확인을 자동으로 하지는 않습니다.
    title=f'[{region}] 현재 날씨 {float(temp):.1f}℃ · {weather_status}'
    content=f'{region} 지역의 기온은 {float(temp):.1f}℃이며 날씨는 {weather_status}입니다. 기상 이벤트: {warning_type}.'
    # 값은 SQL의 %s와 분리해 전달합니다. 블록이 성공하면 공통 DB 도우미가 commit합니다.
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO weather_news(region_id,temp,weather_status,warning_type,news_title,news_content) VALUES(%s,%s,%s,%s,%s,%s)',(found[0]['region_id'],temp,weather_status,warning_type,title,content))
            nid=cur.lastrowid
    # 방금 저장한 ID를 최신 뉴스 목록에서 찾아 돌려줍니다.
    # 목록은 30건이므로 동시 생성이 많을 때 해당 행을 찾지 못할 가능성이 있습니다.
    return next(x for x in list_news() if x['id']==nid)

# 지역별로 create를 호출해 각각 저장합니다. 전체 생성이 하나의 트랜잭션은 아닙니다.
# 반복 실행하면 새 뉴스가 추가되며 기본 warning_type은 '없음'입니다.
def generate():
    created=[]
    for o in observations():
        created.append(create(o['region_name'],o['temperature'],o['weather_status']))
    return {'generatedCount':len(created),'data':created}

