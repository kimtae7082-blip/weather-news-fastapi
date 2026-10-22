"""표준 라이브러리만 사용하는 오프라인 단위 테스트.

httpx/PyMySQL/dotenv를 가짜 모듈로 교체한다. 실제 서버, DB, 외부 API
연결 성공을 검증하는 테스트가 아니다. 실제 서비스 함수는 그대로 실행한다.
"""
import importlib
import asyncio
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
httpx = types.ModuleType('httpx')
httpx.AsyncClient = MagicMock()
pymysql = types.ModuleType('pymysql')
pymysql.connect = MagicMock()
pymysql.cursors = types.SimpleNamespace(DictCursor=object)
dotenv = types.ModuleType('dotenv')
dotenv.load_dotenv = lambda: None
# 모듈을 읽는 동안에만 외부 라이브러리 이름을 대체한다.
with patch.dict(sys.modules, {'httpx': httpx, 'pymysql': pymysql, 'dotenv': dotenv}):
    connection = importlib.import_module('database.connection')
    weather = importlib.import_module('services.weather')
    air = importlib.import_module('services.air')
    climate = importlib.import_module('services.climate')
    news = importlib.import_module('services.news')


class RulesTests(unittest.TestCase):
    def test_status_codes(self):
        for code, expected in [(200, '뇌우'), (300, '이슬비'), (500, '비'),
                               (600, '눈'), (700, '안개/대기현상'), (800, '맑음'),
                               (804, '매우 흐림'), (None, '정보 없음')]:
            with self.subTest(code=code):
                self.assertEqual(weather.status(code), expected)

    def test_event_boundaries(self):
        base = dict(temperature=20, wind_speed=0, precipitation=0, weather_code=800)
        self.assertEqual(weather.event_rules(base), [])
        for field, value, name, level in [
            ('temperature', 33, '폭염', '주의'), ('temperature', 35, '폭염', '경보'),
            ('temperature', -12, '한파', '주의'), ('temperature', -15, '한파', '경보'),
            ('wind_speed', 14, '강풍', '주의'), ('wind_speed', 21, '강풍', '경보'),
            ('precipitation', 30, '호우', '주의'), ('precipitation', 50, '호우', '경보'),
            ('weather_code', 600, '대설', '주의'), ('weather_code', 200, '뇌우', '주의')]:
            with self.subTest(field=field, value=value):
                self.assertEqual(weather.event_rules({**base, field: value})[0][:2], (name, level))

    def test_air_grade_boundaries(self):
        for pm10, limits in [(True, [30, 80, 150]), (False, [15, 35, 75])]:
            self.assertEqual(air.grade(None, pm10), '정보 없음')
            for value, grade in zip(limits, ['좋음', '보통', '나쁨']):
                self.assertEqual(air.grade(value, pm10), grade)
            self.assertEqual(air.grade(limits[-1] + 1, pm10), '매우 나쁨')

    def test_latest_observation_adds_status(self):
        with patch.object(weather, 'query', return_value=[{'weather_code': 800}]):
            self.assertEqual(weather.observations()[0]['weather_status'], '맑음')

    def test_db_commit_and_close(self):
        conn = MagicMock()
        with patch.object(pymysql, 'connect', return_value=conn):
            with connection.db() as actual:
                self.assertIs(actual, conn)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    def test_db_rollback_and_reraise(self):
        conn = MagicMock()
        with patch.object(pymysql, 'connect', return_value=conn):
            with self.assertRaisesRegex(ValueError, '실패'):
                with connection.db():
                    raise ValueError('실패')
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    def test_news_rejects_unknown_region(self):
        with patch.object(news, 'query', return_value=[]):
            with self.assertRaisesRegex(ValueError, '등록되지 않은 지역'):
                news.create('없는 지역', 20, '맑음')

    def test_news_generation_uses_observations(self):
        with patch.object(news, 'observations', return_value=[{
            'region_name': '서울', 'temperature': 20, 'weather_status': '맑음'}]), \
             patch.object(news, 'create', return_value={'id': 1}) as create:
            self.assertEqual(news.generate(), {'generatedCount': 1, 'data': [{'id': 1}]})
            create.assert_called_once_with('서울', 20, '맑음')


class OfflineLoop(asyncio.SelectorEventLoop):
    """가짜 통신만 실행하므로 Windows의 내부 소켓도 열지 않는다."""
    def __init__(self):
        selector = MagicMock()
        selector.select.return_value = []
        selector.get_map.return_value = {}
        super().__init__(selector=selector)

    def _make_self_pipe(self):
        pass

    def _close_self_pipe(self):
        pass

    def _write_to_self(self):
        pass


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    def _setupAsyncioRunner(self):
        self._asyncioRunner = asyncio.Runner(loop_factory=OfflineLoop)

    async def test_collect_requires_key(self):
        with patch.dict(os.environ, {'OPENWEATHER_API_KEY': ''}):
            with self.assertRaisesRegex(ValueError, 'OPENWEATHER_API_KEY'):
                await weather.collect()

    async def test_collect_converts_units_and_counts_failures(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        response = MagicMock()
        response.json.return_value = {'dt': 0, 'main': {'temp': 20, 'humidity': 50},
            'wind': {'speed': 10}, 'weather': [{'id': 800}], 'rain': {'1h': 2}}
        client.get.side_effect = [response, RuntimeError('통신 실패')]
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.rowcount = 1
        context = MagicMock()
        context.__enter__.return_value = conn
        regions = [{'region_id': 1, 'region_name': '서울', 'city_code': 'seoul'},
                   {'region_id': 2, 'region_name': '부산', 'city_code': 'busan'}]
        with patch.dict(os.environ, {'OPENWEATHER_API_KEY': 'fake-test-key'}), \
             patch.object(httpx, 'AsyncClient', return_value=client), \
             patch.object(weather, 'regions', return_value=regions), \
             patch.object(weather, 'db', return_value=context):
            result = await weather.collect()
        self.assertEqual((result['insertedCount'], result['failedCount']), (1, 1))
        args = conn.cursor.return_value.__enter__.return_value.execute.call_args.args[1]
        self.assertEqual(args[3], 36.0)  # 10 m/s -> 36 km/h
        self.assertEqual(args[-1], '1970-01-01 00:00:00')  # DB 저장은 UTC

    async def test_air_failure_is_per_region(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get.side_effect = RuntimeError('통신 실패')
        with patch.object(httpx, 'AsyncClient', return_value=client), \
             patch.object(air, 'regions', return_value=[{
                 'region_id': 1, 'region_name': '서울', 'city_code': 'seoul'}]):
            result = await air.get_air()
        self.assertEqual(result[0]['region_name'], '서울')
        self.assertIn('error', result[0])

    async def test_climate_unknown_region(self):
        with patch.object(climate, 'regions', return_value=[]):
            with self.assertRaises(ValueError):
                await climate.analyze_climate(999)

    async def test_climate_aggregation_ignores_missing_temperature(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        response = MagicMock()
        response.json.return_value = {'daily': {
            'time': ['2016-01-01', '2016-01-02', '2025-01-01'],
            'temperature_2m_mean': [10, None, 12],
            'temperature_2m_max': [33, None, 34], 'precipitation_sum': [1, None, 3]}}
        client.get.return_value = response
        with patch.object(httpx, 'AsyncClient', return_value=client), \
             patch.object(climate, 'regions', return_value=[{
                 'region_id': 1, 'region_name': '서울', 'city_code': 'seoul'}]):
            result = await climate.analyze_climate(1)
        self.assertEqual(result['years'][0]['avgTemperature'], 10)
        self.assertEqual(result['comparison']['temperatureDifference'], 2)
        self.assertEqual(result['comparison']['rainfallDifference'], 2)


if __name__ == '__main__':
    unittest.main()
