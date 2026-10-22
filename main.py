
# ==============================================
# 전국 날씨 뉴스 앱 - FastAPI main.py
# ==============================================

from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database.connection import query
from services.regions import regions
from services import weather, air, climate, news


# ==============================================
# 1. FastAPI 설정
# ==============================================

app = FastAPI(
    title="전국 날씨 뉴스 FastAPI",
    version="1.0.1"
)

PUBLIC = Path(__file__).resolve().parent / "public"

app.mount(
    "/css",
    StaticFiles(directory=PUBLIC / "css"),
    name="css"
)

app.mount(
    "/js",
    StaticFiles(directory=PUBLIC / "js"),
    name="js"
)


# ==============================================
# 2. 공통 응답 함수
# ==============================================

def ok(data=None, **extras):
    result = {"success": True}

    if data is not None:
        result["data"] = data

    result.update(extras)

    return jsonable_encoder(result)


# ==============================================
# 3. 홈페이지
# ==============================================

@app.get("/")
def home():
    return FileResponse(PUBLIC / "index.html")


# ==============================================
# 4. DB 연결 상태
# ==============================================

@app.get("/api/health")
def health():
    try:
        query("SELECT 1")
        return ok(message="MySQL 연결 정상")

    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "DB 연결 실패: " + str(exc)
            }
        )


# ==============================================
# 5. 지역 조회
# ==============================================

@app.get("/api/regions")
def get_regions():
    return ok(regions())


# ==============================================
# 6. 날씨 관측 조회
# ==============================================

@app.get("/api/weather/observations")
def get_observations():
    return ok(weather.observations())


# ==============================================
# 7. 날씨 수집
# ==============================================

@app.post("/api/weather/collect")
async def collect():
    try:
        result = await weather.collect()
        return ok(result, **result)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


# ==============================================
# 8. 기상 현상 분석
# ==============================================

@app.post("/api/weather/analyze")
def analyze():
    return ok(weather.analyze())


# ==============================================
# 9. 기상 이벤트 조회
# ==============================================

@app.get("/api/weather/events")
def events():
    return ok(weather.events())


# ==============================================
# 10. 대기질 조회
# ==============================================

@app.get("/api/air-quality")
async def air_quality():
    data = await air.get_air()

    return ok(
        data,
        count=len(data)
    )


# ==============================================
# 11. 기후 분석
# ==============================================

@app.get("/api/climate/analysis/{region_id}")
async def climate_analysis(region_id: int):
    try:
        return ok(
            await climate.analyze_climate(region_id)
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )


# ==============================================
# 12. 뉴스 목록 조회
# ==============================================

@app.get("/api/weather-news")
def get_news():
    return ok(news.list_news())


# ==============================================
# 13. 뉴스 수동 등록
# ==============================================

class NewsInput(BaseModel):
    region: str
    temp: float
    weather_status: str
    warning_type: str = "없음"


@app.post("/api/weather-news")
def create_news(item: NewsInput):
    try:
        return ok(
            news.create(**item.model_dump())
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


# ==============================================
# 14. 전체 뉴스 자동 생성
# 기존 기능 유지
# ==============================================

@app.post("/api/weather-news/generate")
def generate_news():
    try:
        return ok(news.generate())

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


# ==============================================
# 15. 지역별 뉴스 자동 생성
# 신규 API
#
# POST /api/weather-news/generate/1
# ==============================================

@app.post("/api/weather-news/generate/{region_id}")
def generate_region_news(region_id: int):

    # 요청한 지역이 실제로 존재하는지 확인
    region_rows = query(
        """
        SELECT region_id, region_name
        FROM region
        WHERE region_id = %s
        """,
        (region_id,)
    )

    if not region_rows:
        raise HTTPException(
            status_code=404,
            detail="해당 지역을 찾을 수 없습니다."
        )

    try:
        # 기존 뉴스 자동 생성 함수 실행
        generation_result = news.generate()

        # 생성 후 해당 지역의 뉴스 조회
        region_news = query(
            """
            SELECT
                id,
                region_id,
                temp,
                weather_status,
                warning_type,
                news_title,
                news_content,
                created_at
            FROM weather_news
            WHERE region_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (region_id,)
        )

        return ok(
            region_news,
            message="뉴스 생성 요청이 처리되었습니다.",
            region_id=region_id,
            generation_result=generation_result
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


# ==============================================
# 16. Chrome DevTools 요청 처리
# ==============================================

@app.get(
    "/.well-known/appspecific/com.chrome.devtools.json",
    include_in_schema=False
)
def chrome_devtools():
    return Response(status_code=204)
