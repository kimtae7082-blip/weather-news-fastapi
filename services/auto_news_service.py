from datetime import datetime

from database.connection import query
from services.weather_service import fetch_and_save_weather_data
from services.news_service import generate_region_news


def run_auto_news():
    print("===== 전국 날씨 뉴스 자동 생성 시작 =====")

    # 1. 최신 날씨 수집
    collection = fetch_and_save_weather_data()

    # 2. 지역 목록 조회
    regions = query(
        "SELECT region_id, region_name FROM region ORDER BY region_id"
    )

    results = []
    failed = []

    # 3. 지역별 뉴스 생성
    for region in regions:
        region_id = region["region_id"]

        try:
            news = generate_region_news(region_id)

            results.append({
                "region_id": region_id,
                "region_name": region["region_name"],
                "news_id": news["id"],
                "already_exists": news["already_exists"]
            })

            print(f"[성공] {region['region_name']} 뉴스 생성")

        except Exception as error:
            failed.append({
                "region_id": region_id,
                "region_name": region["region_name"],
                "error": str(error)
            })

            print(f"[실패] {region['region_name']}: {error}")

    return {
        "executed_at": datetime.now().isoformat(),
        "collection": collection,
        "success_count": len(results),
        "failed_count": len(failed),
        "results": results,
        "failed": failed
    }