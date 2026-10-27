# 날씨 수집 → OpenAI 기사 초안 실행 안내

## 만드는 것

OpenWeather의 최신 날씨를 저장한 뒤 OpenAI가 한국어 기사 초안을 작성합니다.
기본 모델은 기존 설정의 gpt-4.1-mini이며 .env에서 바꿀 수 있습니다.
제목·짧은 설명은 AI가 작성하고, 수치·관측 시각·출처·생성 모델·생성 시각은 프로그램이 붙입니다.
AI 문장 내용이 사실인지 완전히 자동 검증하는 기능은 아닙니다. 게시 전 사람이 검수하세요.

## 1. 실행 폴더와 준비

Windows 11의 VS Code에서 weather-news-fastapi 폴더를 엽니다.
main.py, requirements.txt, auto_news.py가 보이는 폴더의 PowerShell에서 실행합니다.

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

정상 확인: Python 버전이 나오고 패키지 충돌이 없어야 합니다.
이번 검증은 Python 3.12.14에서 수행했습니다. Python 3.14.7에서는 설치·실행을 확인하지 못했습니다.

## 2. 키와 DB 설정

.env가 없을 때만 .env.example을 복사해서 .env를 만드세요.
기존 .env가 있으면 덮어쓰지 말고 필요한 항목을 편집합니다.

| 항목 | 입력 |
|---|---|
| DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME | 본인의 기존 MySQL 접속 정보 |
| OPENWEATHER_API_KEY | 본인의 OpenWeather API 키 |
| OPENAI_API_KEY | 본인의 OpenAI API 키 |
| OPENAI_MODEL | 기본 gpt-4.1-mini |

키는 .env에만 입력합니다. 채팅·GitHub·화면 캡처로 공유하지 마세요.
OpenAI API 호출에는 계정의 API 이용 설정과 결제가 필요할 수 있습니다.
기사마다 API 사용 비용이 발생할 수 있습니다. 17개 지역은 한 주기 최대 17회 요청합니다.
실패 요청도 공급자 정책에 따라 비용이 발생할 수 있습니다.

기존 MySQL DB에 region, weather_observation, weather_news 테이블과
대표 지역 좌표에 맞는 city_code가 있어야 합니다.
이 변경은 테이블 생성·삭제·스키마 변경을 실행하지 않습니다.
원래 SQL 파일의 DROP TABLE 구문을 기존 DB에서 실행하지 마세요.

정상 확인: 기존 서버의 /api/health와 /api/regions 조회가 성공해야 합니다.
관측 시각은 services/weather.py 기준 UTC, 풍속은 km/h입니다.
이전 weather_service.py로 저장한 KST·m/s 자료와 혼용하지 말고 최신 자료를 다시 수집하세요.

## 3. 먼저 1회 시험 실행

이 명령은 날씨와 기사 초안을 DB에 저장하고 OpenAI API를 호출합니다.

```powershell
.\.venv\Scripts\python.exe auto_news.py --once
```

정상 확인: '수집 성공 지역', '새 기사', '기존 기사', '실패' 건수가 표시됩니다.
실패 0이며 DB의 weather_news에 [AI 초안] 제목이 생기는지 확인하세요.
동일 관측자료가 이미 처리되었다면 새 기사 0건, 기존 기사 증가가 정상입니다.
수집에 실패한 지역은 그 주기의 기사 작성에서 제외합니다.
관측이 3시간보다 오래됐거나 5분 이상 미래 시각이면 저장하지 않습니다.
관측자료가 모두 실패하면 새 기사는 만들지 않습니다.

## 4. 확인 후 반복 실행

```powershell
.\.venv\Scripts\python.exe auto_news.py
```

실행 즉시 처리하고 작업이 끝난 뒤 1시간 대기합니다. 종료는 Ctrl+C입니다.
컴퓨터·터미널이 켜져 있어야 하며 재부팅 후 자동 시작 기능은 추가하지 않았습니다.
이 명령만으로 웹 서버가 시작되지는 않습니다.
브라우저 조회가 필요하면 다른 터미널에서 기존 서버를 실행하세요.

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 3000
```

서버 시작 로그를 확인한 뒤 http://127.0.0.1:3000 에서 새로고침합니다.
선택 지역 기사 생성 버튼도 같은 OpenAI 경로를 사용하며, 해당 지역만 처리합니다.
버튼은 먼저 저장된 관측을 사용하므로 최신 날씨 수집을 먼저 해야 합니다.
기존 수동 등록 POST /api/weather-news는 문장 틀 방식을 유지합니다.

## 오류 확인 순서

| 증상 | 확인·수정 | 재확인 |
|---|---|---|
| OPENAI_API_KEY 설정 오류 | .env의 예시 값 대신 실제 키 입력 | 서버를 재시작한 뒤 1회 실행 |
| OpenAI 작성 실패 | 키·API 결제·모델 접근 권한·네트워크 확인 | 1회 실행 |
| 수집 실패 | OpenWeather 키·네트워크·DB·지역 좌표 확인 | 먼저 날씨 수집 성공 여부 확인 |
| 오래된 관측 | 컴퓨터 시계·UTC 저장 방식 확인 후 재수집 | 1회 실행 |
| 같은 관측 생성 중 | 다른 실행이 완료될 때까지 기다림 | 생성 기사 목록 확인 |
| DB 오류 | 접속 정보·테이블 및 MySQL GET_LOCK 지원 확인 | /api/health 후 1회 실행 |

오류나 응답 거절 시 AI가 쓴 것처럼 문장 틀로 대신 저장하지 않습니다.
API 응답 원문이나 키가 오류 화면에 노출되지 않도록 생성 실패 메시지는 일반화합니다.
API 응답 후 DB 저장 직전 프로세스가 종료되면 재실행에서 API를 다시 호출할 수 있습니다.
중복 방지는 성공적으로 저장된 관측 기준이며, 무조건 한 번만 결제된다는 보장은 아닙니다.

## 검증과 제출 전 확인

외부 연결 없는 Python 테스트 22개 통과(Python 3.12.14).
실제 OpenAI·OpenWeather·MySQL 통합 실행, Python 3.14.7, 브라우저 렌더링은 미검증입니다.
수치·UTC/KST·단위·지역과 AI가 덧붙인 해석·인용·공식 특보 표현을 사람이 검수하세요.
실제 사용 모델·생성 시각은 기사 본문에 남습니다.

공식 구현 참고:
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/api/docs/models/gpt-4.1-mini
