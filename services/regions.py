# city_code와 대표 위도·경도(위도, 경도 순서)의 연결표입니다.
# 대표 지점의 날씨이므로 시·도 전체의 모든 위치를 나타내지는 않습니다.
COORDS = {
'seoul':(37.5665,126.9780),'busan':(35.1796,129.0756),'daegu':(35.8714,128.6014),'incheon':(37.4563,126.7052),'gwangju':(35.1595,126.8526),'daejeon':(36.3504,127.3845),'ulsan':(35.5384,129.3114),'sejong':(36.4800,127.2890),'gyeonggi':(37.4138,127.5183),'gangwon':(37.8228,128.1555),'chungbuk':(36.8,127.7),'chungnam':(36.5184,126.8),'jeonbuk':(35.8203,127.1089),'jeonnam':(34.8679,126.991),'gyeongbuk':(36.4919,128.8889),'gyeongnam':(35.4606,128.2132),'jeju':(33.4996,126.5312)}
from database.connection import query

# 좌표는 위 상수에서, 지역 번호와 이름은 기존 MySQL region 테이블에서 읽습니다.
# DB city_code가 COORDS의 키와 같아야 외부 API를 조회할 수 있습니다.
def regions():
    return query('SELECT region_id, city_code, region_name FROM region ORDER BY region_id')

