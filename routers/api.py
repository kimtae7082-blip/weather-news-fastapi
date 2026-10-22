from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database.connection import query
from services import weather_service as weather, air_quality_service as air, climate_service as climate
from services.news_service import generate_region_news

router = APIRouter(prefix='/api')

def fail(exc, message):
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail={'success': False, 'message': str(exc)}) from exc
    print(f'{message}: {exc}')
    raise HTTPException(status_code=500, detail={'success': False, 'message': message, 'error': str(exc)}) from exc

@router.get('/health')
def health():
    try:
        query('SELECT 1')
        return {'success': True, 'database': 'connected', 'message': '서버와 데이터베이스가 정상적으로 연결되었습니다.'}
    except Exception as exc: fail(exc, '데이터베이스 연결에 실패했습니다.')

@router.get('/regions')
def regions():
    try: return {'success': True, 'data': weather.get_all_regions()}
    except Exception as exc: fail(exc, '지역 목록을 불러오지 못했습니다.')

@router.post('/weather/collect')
def collect():
    try: return {'success': True, 'message': '전국 17개 시·도 날씨 데이터 수집이 완료되었습니다.', 'result': weather.fetch_and_save_weather_data()}
    except Exception as exc: fail(exc, '날씨 데이터를 수집하지 못했습니다.')

@router.get('/weather/observations')
def observations():
    try: return {'success': True, 'data': weather.get_latest_observations()}
    except Exception as exc: fail(exc, '날씨 데이터를 불러오지 못했습니다.')

@router.post('/weather/analyze')
def analyze():
    try: return {'success': True, 'message': '기상 이벤트 분석이 완료되었습니다.', 'result': weather.analyze_and_save_events()}
    except Exception as exc: fail(exc, '기상 이벤트 분석에 실패했습니다.')

from fastapi import HTTPException
import traceback

@router.get('/weather/events')
def events():
    try:
        return {
            'success': True,
            'data': weather.get_latest_events()
        }

    except Exception as exc:
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

@router.get('/weather-news')
def news():
    try: return {'success': True, 'data': weather.get_all_news()}
    except Exception as exc: fail(exc, '날씨 뉴스를 불러오지 못했습니다.')

class NewsInput(BaseModel):
    region: str
    temp: float
    weather_status: str
    warning_type: str = '없음'

@router.post('/weather-news', status_code=201)
def create_news(body: NewsInput):
    try:
        return {'success': True, 'message': '날씨 뉴스가 생성되었습니다.',
                'data': weather.create_news(body.region, body.temp, body.weather_status, body.warning_type)}
    except Exception as exc: fail(exc, '날씨 뉴스 생성에 실패했습니다.')

@router.post('/weather-news/generate')
def generate():
    try: return {'success': True, 'message': '전국 날씨 뉴스 생성이 완료되었습니다.', 'data': weather.generate_news_article()}
    except Exception as exc: fail(exc, '뉴스 자동 생성에 실패했습니다.')

@router.get('/air-quality')
def air_quality():
    try:
        data = air.fetch_air_quality()
        return {'success': True, 'count': len(data), 'data': data}
    except Exception as exc: fail(exc, '미세먼지 조회 실패')

@router.get('/climate/analysis/{region_id}')
def climate_analysis(region_id: int):
    if region_id < 1: raise HTTPException(status_code=400, detail='올바른 지역 ID를 입력하세요.')
    try: return {'success': True, 'data': climate.get_climate_analysis(region_id)}
    except Exception as exc: fail(exc, '기후 분석 오류')

# =====================================
# 지역별 날씨 뉴스 자동 생성 API
# =====================================

@router.post("/weather-news/generate/{region_id}")
def create_weather_news(region_id: int):

    if region_id < 1:
        raise HTTPException(
            status_code=400,
            detail="올바른 지역 ID를 입력하세요."
        )

    try:
        news = generate_region_news(region_id)

        return {
            "success": True,
            "message": "날씨 뉴스 생성 완료",
            "data": news
        }

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except Exception as error:
        print("뉴스 생성 오류:", error)

        raise HTTPException(
            status_code=500,
            detail="날씨 뉴스 생성 중 오류가 발생했습니다."
        )
