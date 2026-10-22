
from datetime import datetime
from database.connection import connection


def describe_weather(temp, rain, wind):
    """관측값을 바탕으로 날씨 상태를 설명합니다."""
    if rain >= 30:
        return "강한 비가 내리고 있습니다"
    if rain > 0:
        return "비가 내리고 있습니다"
    if wind >= 14:
        return "바람이 강하게 불고 있습니다"
    if temp >= 33:
        return "무더운 날씨를 보이고 있습니다"
    if temp <= -12:
        return "매우 추운 날씨를 보이고 있습니다"
    return "현재 기상 상황이 비교적 안정적입니다"


def describe_warning(temp, rain, wind):
    """공식 특보가 아닌 자체 분석 결과입니다."""
    warnings = []

    if temp >= 33:
        warnings.append("폭염 주의")
    if temp <= -12:
        warnings.append("한파 주의")
    if rain >= 30:
        warnings.append("강한 강수 주의")
    if wind >= 14:
        warnings.append("강풍 주의")

    return ", ".join(warnings) if warnings else "없음"


def generate_region_news(region_id):
    with connection() as db:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.region_id,
                    r.region_name,
                    w.temperature,
                    w.humidity,
                    w.wind_speed,
                    w.precipitation,
                    w.observed_at
                FROM region r
                JOIN weather_observation w
                  ON w.region_id = r.region_id
                WHERE r.region_id = %s
                ORDER BY w.observed_at DESC,
                         w.observation_id DESC
                LIMIT 1
                """,
                (region_id,)
            )

            weather = cursor.fetchone()

            if not weather:
                raise ValueError(
                    "선택한 지역의 날씨 관측 데이터가 없습니다."
                )

            name = weather["region_name"]
            temp = float(weather["temperature"])
            humidity = int(weather["humidity"])
            wind = float(weather["wind_speed"])
            rain = float(weather["precipitation"] or 0)

            status = describe_weather(temp, rain, wind)
            warning = describe_warning(temp, rain, wind)

            observed_at = weather["observed_at"]

            title = (
                f"[{name}] 현재 기온 {temp:.1f}℃, "
                f"{'강수 관측' if rain > 0 else '지역 날씨 현황'}"
            )

            content = (
                f"{name}의 최근 관측 날씨를 전해드립니다.\n\n"
                f"관측 시각은 {observed_at}이며, "
                f"현재 기온은 {temp:.1f}℃, "
                f"습도는 {humidity}%, "
                f"풍속은 {wind:.1f}km/h입니다.\n\n"
                f"관측 강수량은 {rain:.1f}mm이며, "
                f"{status}.\n\n"
                f"자체 기상 위험 분석 결과: {warning}.\n\n"
                "이 기사는 관측 데이터를 바탕으로 "
                "자동 생성되었으며, "
                "공식 기상특보나 예보를 대신하지 않습니다."
            )

            # 동일 지역, 동일 관측 시각의 중복 생성 방지
            cursor.execute(
                """
                SELECT id
                FROM weather_news
                WHERE region_id = %s
                  AND news_title = %s
                  AND news_content = %s
                LIMIT 1
                """,
                (region_id, title, content)
            )

            existing = cursor.fetchone()

            if existing:
                return {
                    "id": existing["id"],
                    "region_id": region_id,
                    "news_title": title,
                    "news_content": content,
                    "already_exists": True
                }

            cursor.execute(
                """
                INSERT INTO weather_news (
                    region_id,
                    temp,
                    weather_status,
                    warning_type,
                    news_title,
                    news_content
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    region_id,
                    temp,
                    status[:50],
                    warning[:100],
                    title,
                    content
                )
            )

            news_id = cursor.lastrowid

            return {
                "id": news_id,
                "region_id": region_id,
                "news_title": title,
                "news_content": content,
                "already_exists": False
            }

