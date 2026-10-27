"""--once는 1회 실행, 옵션 없이 실행하면 1시간마다 반복한다."""
import argparse
import time
from services.auto_news_service import run_auto_news


def main():
    parser = argparse.ArgumentParser(description='날씨 수집 및 OpenAI 기사 초안 자동 생성')
    parser.add_argument('--once', action='store_true', help='1회 실행 후 종료')
    args = parser.parse_args()
    while True:
        try:
            result = run_auto_news()
            print('수집 성공 지역:', len(result['collection']['collectedRegionIds']))
            print('새 기사:', result['generatedCount'], '기존 기사:', result['existingCount'],
                  '실패:', result['failed_count'])
            if args.once and result['failed_count']:
                raise SystemExit(1)
        except Exception:
            print('자동 생성 실패: .env 설정, DB 및 API 상태를 확인하세요.')
            if args.once:
                raise SystemExit(1)
        if args.once:
            return
        print('다음 실행까지 1시간 대기합니다. 종료: Ctrl+C')
        time.sleep(3600)


if __name__ == '__main__':
    main()

