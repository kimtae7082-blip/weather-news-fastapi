# Open-Meteo 대기질 자료를 조회하는 서비스입니다. 이 파일에서는 DB에 저장하지 않습니다.
import asyncio
import httpx
from services.regions import regions,COORDS

# 수치 구간을 한국어 등급으로 표시합니다. None은 0이 아니라 '정보 없음'입니다.
# pm10=True는 PM10, False는 PM2.5 구간을 선택합니다. 공식 기준 여부는 별도 검증하세요.
def grade(v,pm10):
    if v is None:return '정보 없음'
    limits=[30,80,150] if pm10 else [15,35,75]
    return next((g for n,g in zip(limits,['좋음','보통','나쁨']) if v<=n),'매우 나쁨')

# 하나의 HTTP 클라이언트를 공유하고 여러 지역의 요청을 함께 기다립니다.
async def get_air():
    async with httpx.AsyncClient(timeout=25) as client:
        async def one(r):
            try:
                lat,lon=COORDS[r['city_code']]
                resp=await client.get('https://air-quality-api.open-meteo.com/v1/air-quality',params={'latitude':lat,'longitude':lon,'current':'pm10,pm2_5','timezone':'Asia/Seoul'})
                resp.raise_for_status(); c=resp.json()['current']; p=c.get('pm10');f=c.get('pm2_5')
                return {'region_id':r['region_id'],'region_name':r['region_name'],'pm10':p,'pm25':f,'pm10_grade':grade(p,True),'pm25_grade':grade(f,False),'observed_at':c.get('time')}
            # 지역별 실패를 error 항목으로 반환하므로 다른 지역의 성공 결과는 유지합니다.
            except Exception as exc:return {'region_id':r['region_id'],'region_name':r['region_name'],'error':str(exc)}
        # gather 결과의 순서는 입력한 지역 순서를 따릅니다.
        return await asyncio.gather(*(one(r) for r in regions()))

# Open-Meteo 대기질 자료를 조회하는 서비스입니다. 이 파일에서는 DB에 저장하지 않습니다.
import asyncio
import httpx
from services.regions import regions,COORDS

# 수치 구간을 한국어 등급으로 표시합니다. None은 0이 아니라 '정보 없음'입니다.
# pm10=True는 PM10, False는 PM2.5 구간을 선택합니다. 공식 기준 여부는 별도 검증하세요.
def grade(v,pm10):
    if v is None:return '정보 없음'
    limits=[30,80,150] if pm10 else [15,35,75]
    return next((g for n,g in zip(limits,['좋음','보통','나쁨']) if v<=n),'매우 나쁨')

# 하나의 HTTP 클라이언트를 공유하고 여러 지역의 요청을 함께 기다립니다.
async def get_air():
    async with httpx.AsyncClient(timeout=25) as client:
        async def one(r):
            try:
                lat,lon=COORDS[r['city_code']]
                resp=await client.get('https://air-quality-api.open-meteo.com/v1/air-quality',params={'latitude':lat,'longitude':lon,'current':'pm10,pm2_5','timezone':'Asia/Seoul'})
                resp.raise_for_status(); c=resp.json()['current']; p=c.get('pm10');f=c.get('pm2_5')
                return {'region_id':r['region_id'],'region_name':r['region_name'],'pm10':p,'pm25':f,'pm10_grade':grade(p,True),'pm25_grade':grade(f,False),'observed_at':c.get('time')}
            # 지역별 실패를 error 항목으로 반환하므로 다른 지역의 성공 결과는 유지합니다.
            except Exception as exc:return {'region_id':r['region_id'],'region_name':r['region_name'],'error':str(exc)}
        # gather 결과의 순서는 입력한 지역 순서를 따릅니다.
        return await asyncio.gather(*(one(r) for r in regions()))
