import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import test_services
ai_news, news = test_services.ai_news, test_services.news
import sys
with patch.dict(sys.modules, {'database.connection': test_services.connection,
                             'services.weather': test_services.weather,
                             'services.news': news}):
    from services import auto_news_service


class AINewsTests(unittest.TestCase):
    def observation(self):
        return dict(region_id=1, region_name='서울', temperature=20, humidity=50,
                    wind_speed=36, precipitation=0, weather_status='맑음',
                    observed_at=datetime.now(timezone.utc))

    def test_placeholder_key_rejected(self):
        with patch.dict(os.environ, OPENAI_API_KEY='YOUR_OPENAI_KEY'):
            with self.assertRaises(ValueError):
                ai_news.configuration()

    def test_stale_observation_rejected(self):
        o = self.observation()
        o['observed_at'] -= timedelta(hours=4)
        with self.assertRaises(ValueError):
            ai_news.facts_for(o)

    def test_missing_measurement_not_invented(self):
        o = self.observation()
        o['humidity'] = float('nan')
        with self.assertRaises(ValueError):
            ai_news.facts_for(o)

    def test_response_and_request_contract(self):
        client = MagicMock()
        response = client.post.return_value
        response.status_code = 200
        response.json.return_value = {'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text',
              'text': json.dumps({'title': '서울의 맑은 날씨', 'body': '서울에서 맑은 날씨가 관측됐습니다.'})}]}]}
        fake = MagicMock()
        fake.Client.return_value.__enter__.return_value = client
        fake.RequestError = RuntimeError
        with patch.object(ai_news, 'httpx', fake):
            title, _ = ai_news.request_article({'temperature': 20}, 'fake-key', 'gpt-4.1-mini')
        self.assertEqual(title, '서울의 맑은 날씨')
        payload = client.post.call_args.kwargs['json']
        self.assertFalse(payload['store'])
        self.assertTrue(payload['text']['format']['strict'])

    def test_numeric_generated_claim_rejected(self):
        fake = MagicMock()
        fake.RequestError = RuntimeError
        response = fake.Client.return_value.__enter__.return_value.post.return_value
        response.status_code = 200
        response.json.return_value = {'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text',
              'text': '{"title":"기온 99도","body":"잘못된 수치"}'}]}]}
        with patch.object(ai_news, 'httpx', fake):
            with self.assertRaises(ValueError):
                ai_news.request_article({}, 'fake-key', 'model')

    def test_existing_observation_does_not_call_openai(self):
        cur = MagicMock()
        cur.fetchone.side_effect = [{'acquired': 1}, {'id': 9, 'news_title': '기존 기사'}]
        context = MagicMock()
        context.__enter__.return_value.cursor.return_value.__enter__.return_value = cur
        with patch.object(ai_news, 'configuration', return_value=('key', 'model')), \
             patch.object(ai_news, 'db', return_value=context), \
             patch.object(ai_news, 'request_article') as request:
            result = ai_news.generate_observation(self.observation())
        self.assertTrue(result['already_exists'])
        request.assert_not_called()

    def test_only_requested_region_generated(self):
        with patch.object(news, 'observations', return_value=[{'region_id': 1}, {'region_id': 2}]), \
             patch.object(ai_news, 'configuration'), \
             patch.object(ai_news, 'generate_observation',
                          return_value={'already_exists': False}) as generate:
            news.generate(region_ids={2})
        generate.assert_called_once_with({'region_id': 2})

    def test_new_article_saves_facts_and_commits_before_unlock(self):
        cur = MagicMock()
        cur.fetchone.side_effect = [{'acquired': 1}, None]
        cur.lastrowid = 10
        context = MagicMock()
        conn = context.__enter__.return_value
        conn.cursor.return_value.__enter__.return_value = cur
        calls = []
        conn.commit.side_effect = lambda: calls.append('commit')
        cur.execute.side_effect = lambda sql, args: calls.append(sql)
        with patch.object(ai_news, 'configuration', return_value=('key', 'model')), \
             patch.object(ai_news, 'db', return_value=context), \
             patch.object(ai_news, 'request_article', return_value=('맑은 날씨', '서울의 날씨입니다.')):
            result = ai_news.generate_observation(self.observation())
        self.assertIn('36.0km/h', result['news_content'])
        self.assertIn('OpenWeather', result['news_content'])
        self.assertIn('모델: model', result['news_content'])
        self.assertFalse(result['already_exists'])
        self.assertLess(calls.index('commit'), calls.index('SELECT RELEASE_LOCK(%s)'))

    def test_collection_failure_excludes_region(self):
        async def collect():
            return {'collectedRegionIds': [2], 'failedCount': 1}
        import asyncio
        runner = asyncio.Runner(loop_factory=test_services.OfflineLoop)
        with runner, patch.object(auto_news_service, 'configuration'), \
             patch.object(auto_news_service.asyncio, 'run', side_effect=runner.run), \
             patch.object(auto_news_service.weather, 'collect', collect), \
             patch.object(auto_news_service.news, 'generate', return_value={
                 'generatedCount': 1, 'failedCount': 0}) as generate:
            result = auto_news_service.run_auto_news()
        generate.assert_called_once_with(region_ids={2})
        self.assertEqual(result['failed_count'], 1)
