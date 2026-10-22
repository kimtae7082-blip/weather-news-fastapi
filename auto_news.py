import time
from datetime import datetime

from services.auto_news_service import run_auto_news


def main():
    print("전국 날씨 뉴스 자동 실행 프로그램 시작")
    print("실행 간격: 1시간")

    while True:
        try:
            print(f"\n실행 시각: {datetime.now()}")

            result = run_auto_news()

            print("생성 결과")
            print("성공:", result["success_count"])
            print("실패:", result["failed_count"])

        except Exception as error:
            print("자동 실행 오류:", error)

        # 3600초 = 1시간
        time.sleep(3600)


if __name__ == "__main__":
    main()