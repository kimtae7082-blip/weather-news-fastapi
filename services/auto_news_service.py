"""웹 앱과 동일한 날씨 수집·AI 기사 생성 경로."""
import asyncio
from datetime import datetime, timezone
from services import weather, news
from services.ai_news import configuration


def run_auto_news():
    configuration()
    collection = asyncio.run(weather.collect())
    result = news.generate(region_ids=set(collection['collectedRegionIds']))
    return {'executed_at': datetime.now(timezone.utc).isoformat(),
            'collection': collection, **result,
            'success_count': result['generatedCount'],
            'failed_count': collection['failedCount'] + result['failedCount']}

