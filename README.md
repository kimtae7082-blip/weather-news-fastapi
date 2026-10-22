# 전국 날씨 뉴스 FastAPI (Korea Weather News)

## 1. 프로젝트 소개

17개 시·도의 대표 지점 날씨, 대기질, 과거 기후 자료와 날씨 뉴스 초안을 보여 주는 학습용 대시보드입니다. 데이터 저널리즘과 Python을 처음 배우는 학습자를 대상으로 합니다.

뉴스는 관측값을 **정해진 문장 틀**에 넣어 생성합니다. 현재 코드에는 생성형 AI 모델 호출이 없습니다.

화면 이미지 자리: 실제 실행 화면을 검수한 뒤 여기에 추가하세요. 이 문서에는 검증하지 않은 화면 이미지를 넣지 않았습니다.

## 2. 기능정의서

| 기능 | 구현 위치 | 동작 |
|---|---|---|
| 지역·최신 관측 조회 | services/regions.py, services/weather.py | 기존 MySQL 조회 |
| 현재 날씨 수집 | services/weather.py | OpenWeather 조회 후 관측 저장 |
| 기상 이벤트 분석 | services/weather.py | 자체 임계값으로 분석 후 저장 |
| 대기질 조회 | services/air.py | Open-Meteo 조회, 지역별 오류 분리 |
| 기후 분석 | services/climate.py | 2016~2025년 자료의 연도별 집계 |
| 뉴스 조회·생성 | services/news.py | 문장 틀 기반 초안 저장 |
| 웹 화면·API | main.py, public/ | 같은 FastAPI 서버에서 제공 |

새로고침은 조회만 수행합니다. 수집·분석·뉴스 생성은 별도의 POST 요청이 필요하며 자동 정기 실행 기능은 없습니다.

## 3. 화면구성도

public/index.html에는 전국 요약 → 지역별 날씨 → 미세먼지 → 기후 분석 → 기상 이벤트 → 주요 기상 현상 → 오늘의 뉴스 영역이 있습니다. public/js/main.js가 API 응답을 화면에 넣습니다. 이는 소스 구조를 확인한 설명이며 실제 브라우저 렌더링 검증 결과는 아닙니다.

## 4. DB 설계와 전제

기존 MySQL weather_korea의 region, weather_observation, weather_event, weather_news 테이블을 사용합니다. 이 폴더에는 DB 생성·삭제·마이그레이션 기능이 없습니다.

- region의 city_code는 services/regions.py의 COORDS 키와 일치해야 합니다.
- 관측은 (region_id, observed_at), 이벤트는 (observation_id, event_type)의 중복 키를 전제로 갱신합니다.
- 같은 저장소의 ../weather-news-app/sql/schema.sql에서 필요한 열과 키를 참고할 수 있습니다. **해당 파일에는 DROP TABLE이 있으므로 기존 DB에 통째로 실행하지 마세요.** 초기 예시 뉴스의 수치도 실제 관측으로 사용하면 안 됩니다.
- DB가 없다면 먼저 별도 테스트 DB를 준비하고 필요한 구조를 확인해야 합니다. 아래 실행 명령만으로 DB가 만들어지지는 않습니다.

## 5. 데이터 수집 방법과 해석

| 자료 | 코드에서 요청하는 공급자 | 처리 |
|---|---|---|
| 현재 날씨 | OpenWeather /data/2.5/weather | API 키 필요, metric 요청, 풍속 m/s를 km/h로 변환해 저장 |
| 대기질 | Open-Meteo air-quality API | PM10·PM2.5 모델 자료 조회, 이 코드에서는 DB 저장 안 함 |
| 과거 기후 | Open-Meteo archive API | 2016-01-01~2025-12-31 고정 조회, 연도별 평균·합계 집계 |

이 표는 코드의 요청 내용을 설명합니다. 공급자의 현재 이용 조건·출처 표기·요금·재배포 허용 여부는 기사 공개 전에 별도로 확인해야 합니다.

- 관측 시각은 UTC 문자열로 DB에 저장됩니다. 한국 시각이라고 단정하지 마세요.
- 화면의 전국 평균은 조회된 대표 지점들의 단순 평균입니다.
- 기상 이벤트의 '주의·경보'는 자체 규칙이며 공식 기상특보가 아닙니다.
- 기후 분석의 첫해와 마지막 해 차이는 장기 추세 검정이나 원인 분석이 아닙니다.
- 뉴스 자동 생성 시 warning_type은 기본 '없음'이며 분석한 이벤트가 자동 결합되지 않습니다.
- 뉴스 생성은 반복할 때 새 행을 추가합니다. 이벤트 조회에는 과거 이벤트도 남아 있습니다.

## 6. 개발 환경과 폴더

```text
weather-news-fastapi/
├─ main.py                 # URL과 처리 함수 연결, 정적 파일 제공
├─ requirements.txt        # 서버 실행에 필요한 패키지 범위
├─ .env.example            # 설정 예시
├─ database/connection.py  # DB 연결, commit·rollback
├─ services/               # 지역·날씨·대기질·기후·뉴스
├─ public/                 # HTML, CSS, JavaScript
├─ routers/__init__.py     # 현재 비어 있음; API는 main.py에 정의
└─ tests/                  # 외부 연결 없는 단위 테스트
```

사용 환경은 Windows 11 PowerShell을 기준으로 안내합니다. Python 3.14.7은 학습자의 목표 버전이며 **이 작업 환경에서 실행 검증하지 못했습니다.** 실제 검증 도구는 Python 3.12.14, Node.js 24.21.0입니다. 의존성 설치 및 Python 3.14.7 호환성은 해당 환경에서 추가 확인이 필요합니다. requirements.txt는 버전 범위로 지정되어 있어 설치 시점에 따라 세부 버전이 달라질 수 있습니다.

Node.js는 선택적인 JavaScript 단위 테스트에만 사용합니다. 이 FastAPI 프로젝트 실행에 npm install이나 Node 서버는 필요하지 않습니다.

## 7. 실행 방법

다음은 실제 파일·함수·API 경로를 대조한 실행 절차입니다. 현재 작업 환경은 패키지 설치와 외부 연결이 제한되어 있어 **서버 기동, 실제 MySQL, 외부 API 호출, 브라우저 화면까지 검증한 실행법은 아닙니다.**

### 7-1. 실행 위치와 Python 확인

VS Code에서 my-explore의 **weather-news-fastapi 폴더**를 열고 새 PowerShell 터미널을 엽니다. main.py와 requirements.txt가 보이는 위치여야 합니다. 기존 Node 서버가 3000번을 사용한다면 그 서버 터미널에서 Ctrl+C로 종료합니다.

```powershell
Get-Location
Get-ChildItem main.py, requirements.txt
py --version
```

정상 확인: 두 파일이 표시되고 Python 버전이 출력됩니다. 목표인 3.14.7과 다르면 설치된 버전을 먼저 확인하세요.

### 7-2. 가상환경과 의존성 준비

가상환경은 이 프로젝트 전용 패키지를 담는 폴더입니다. 활성화 없이 전용 Python을 직접 실행하면 PowerShell 활성화 정책을 바꿀 필요가 없습니다.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

정상 확인: 설치가 오류 없이 끝나고 pip check가 충돌을 보고하지 않습니다. 설치 실패 상태에서 다음 단계로 진행하지 마세요.

### 7-3. 설정과 기존 DB 확인

```powershell
Copy-Item .env.example .env
```

.env가 이미 있다면 복사하지 말고 기존 파일을 편집하세요. 실제 설정은 다음과 같습니다.

| 변수 | 입력할 값 |
|---|---|
| DB_HOST, DB_PORT | MySQL 주소와 포트, 기본 localhost / 3306 |
| DB_USER, DB_PASSWORD | 해당 DB에 접근 가능한 계정과 암호 |
| DB_NAME | 기존 DB 이름, 기본 weather_korea |
| OPENWEATHER_API_KEY | 본인 OpenWeather API 키 |
| PORT | 예시 파일에는 있으나 현재 main.py는 읽지 않음. 실행 명령의 --port 사용 |

.env의 비밀번호·키를 Git에 커밋하거나 화면 캡처로 공유하지 마세요. MySQL 도구에서 아래 **조회문만** 실행해 구조를 확인합니다.

```sql
USE weather_korea;
SHOW TABLES;
SELECT region_id, city_code, region_name FROM region ORDER BY region_id;
SHOW INDEX FROM weather_observation;
SHOW INDEX FROM weather_event;
```

정상 확인: 네 테이블, COORDS에 맞는 17개 지역, 관측·이벤트 중복 키가 있어야 합니다. 누락되면 먼저 DB 준비 상태를 해결하세요. 이 작업에서는 실제 DB에 연결해 확인하지 못했습니다.

### 7-4. 서버 실행

동일한 weather-news-fastapi 폴더에서 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 3000
```

정상 확인: Uvicorn 시작 로그에 오류가 없어야 합니다. 브라우저에서 [대시보드](http://127.0.0.1:3000), [API 문서](http://127.0.0.1:3000/docs)를 엽니다. 종료는 서버 터미널에서 Ctrl+C입니다.

새 PowerShell 터미널에서 DB 연결과 지역 목록을 확인합니다.

```powershell
Invoke-RestMethod http://127.0.0.1:3000/api/health
Invoke-RestMethod http://127.0.0.1:3000/api/regions
```

정상 확인: health의 success가 True이며 지역 응답에 data가 있어야 합니다. health는 외부 날씨 API의 정상 여부를 검사하지 않습니다.

### 7-5. 수집 → 분석 → 뉴스 생성

아래 POST는 **DB를 변경**합니다. 테스트용 DB에서 한 단계씩 실행하고 각 결과를 확인하세요.

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:3000/api/weather/collect
```

정상 확인: data 및 최상위 집계의 insertedCount, skippedCount, failedCount, errors를 봅니다. success=True여도 지역별 실패가 있을 수 있습니다. skippedCount에는 기존 관측 갱신도 포함됩니다.

```powershell
Invoke-RestMethod http://127.0.0.1:3000/api/weather/observations
Invoke-RestMethod -Method Post http://127.0.0.1:3000/api/weather/analyze
```

정상 확인: 최신 관측이 있고 분석 결과에 analyzedCount와 savedEventCount가 나옵니다. 기준을 충족하는 관측이 없으면 이벤트 0건도 정상입니다.

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:3000/api/weather-news/generate
Invoke-RestMethod http://127.0.0.1:3000/api/weather-news
```

정상 확인: generatedCount와 저장된 뉴스 목록을 확인한 뒤 화면의 새로고침을 누릅니다. 관측이 없으면 생성 0건일 수 있습니다. 반복 생성하면 중복 내용의 새 뉴스가 쌓입니다.

대기질과 기후 분석은 다음 GET으로 별도 확인합니다. 기후 지역 번호는 /api/regions 응답에서 선택하세요.

```powershell
Invoke-RestMethod http://127.0.0.1:3000/api/air-quality
$regionId = 1 # 실제 지역 목록에 존재하는 번호로 바꾸세요.
Invoke-RestMethod "http://127.0.0.1:3000/api/climate/analysis/$regionId"
```

### 7-6. 오류가 나면

| 증상 | 코드상 가능한 원인 | 수정 후 재확인 |
|---|---|---|
| main 모듈을 못 찾음 | 실행 폴더가 다름 | main.py가 있는 위치에서 재실행 |
| 패키지를 못 찾음 | 설치 실패 또는 다른 Python 사용 | .venv의 Python으로 설치·실행 |
| 3000 포트 사용 중 | 다른 서버 실행 중 | 기존 서버 종료 또는 --port 변경 후 URL도 변경 |
| health가 503 | DB 접속 정보·서버 상태 문제 | .env와 DB 확인 후 health 재요청 |
| 수집이 400 | API 키 미입력·예시 값 | 실제 키 설정 후 서버 재시작 |
| 수집 failedCount > 0 | 지역 코드·인증·통신·DB 오류 | errors 내용을 확인해 해당 원인 수정 |
| 대기질 일부 지역에 error | 외부 통신 실패 등 | 해당 지역 응답을 확인하고 재조회 |

## 8. 테스트 항목

### 8-1. 자동 단위 테스트

실행 위치는 weather-news-fastapi 폴더입니다. Python 테스트는 표준 라이브러리 unittest만 사용합니다. 외부 라이브러리의 이름을 가짜 모듈로 대체하고 실제 서비스 함수를 검사하므로 의존성 설치 없이도 실행할 수 있습니다.

```powershell
py -m unittest discover -s tests -p "test_*.py" -v
```

정상 결과: **13 tests, OK**. 설치한 가상환경을 사용하려면 py 대신 .\.venv\Scripts\python.exe를 사용하세요. 비동기 테스트도 가짜 통신만 사용하며, 테스트 전용 이벤트 루프로 소켓을 열지 않습니다.

Node.js가 있다면 프런트엔드 함수도 검사할 수 있습니다. npm 패키지는 필요하지 않습니다.

```powershell
node --check public/js/main.js
node --test tests/frontend.test.cjs
```

정상 결과: 문법 검사는 오류 없이 끝나고 **5 tests, pass 5**가 나옵니다.

| 검사 범위 | 확인한 내용 |
|---|---|
| 날씨·이벤트 | 날씨 코드, 자체 임계값 경계, 최신 관측의 날씨 이름 |
| 수집 | API 키 누락, m/s → km/h, UTC 저장값, 일부 지역 실패 집계 |
| DB 도우미 | 성공 시 commit·close, 실패 시 rollback·오류 재전달 |
| 대기질·기후 | 등급 경계·결측, 지역별 오류, 기후 연도 집계 |
| 뉴스 | 없는 지역 거절, 관측값으로 생성 호출 |
| 화면 함수 | HTTP·success 오류, 정상 응답, 빈 관측, 평균·최고·최저 |

### 8-2. 이번 변경의 검증 결과

- 주석 추가 전후 Python 13개와 JavaScript 5개 테스트가 모두 통과했습니다.
- 기존 Python 파일의 실행 구문(AST)을 변경 전과 비교해 동일함을 확인했습니다.
- JavaScript는 추가한 주석 행을 제거하면 원본과 동일하며 문법 검사도 통과했습니다.
- 실제 검증 환경: Python 3.12.14, Node.js 24.21.0. Python 3.14.7에서는 미검증입니다.
- 가짜 DB·HTTP·화면 객체로 검사했습니다. FastAPI 요청 검증(422 등), 실제 트랜잭션·SQL 제약조건·외부 API·브라우저 화면은 이 테스트가 보장하지 않습니다.

### 8-3. 실제 환경에서 남은 확인

- [ ] health 성공 및 지역 17개와 city_code 일치 확인
- [ ] 테스트 DB에서 수집 → 관측 조회 → 분석 → 뉴스 생성 순서 확인
- [ ] 같은 관측 재수집 시 DB 중복 키와 집계 동작 확인
- [ ] 빈 DB·잘못된 키·외부 API 실패 시 안내 확인
- [ ] /docs에서 잘못된 뉴스 요청(422), 없는 기후 지역(404) 확인
- [ ] 대시보드의 지역 선택·새로고침·오류 표시를 실제 브라우저에서 확인
- [ ] Python 3.14.7에서 패키지 설치와 동일 테스트 재실행

### 8-4. 기사 제출 전 검수

- [ ] 수치·기준 시각·단위·지역을 원자료와 대조했는가?
- [ ] 자체 이벤트를 공식 특보로, 두 해 차이를 장기 추세로 표현하지 않았는가?
- [ ] 모델 자료·대표 지점의 한계와 출처·이용 조건을 확인했는가?
- [ ] 자동 생성 초안을 사람이 검수하고 예시 데이터를 제거했는가?
- [ ] 비밀번호·키 등 개인정보·인증정보가 결과물에 없는가?

현재 API에는 인증이 없고, 일부 뉴스 문자열을 innerHTML에 넣으며, health 오류 응답에 DB 오류 내용이 포함됩니다. 이번 변경은 학습용 주석과 문서·테스트만 추가했습니다. 실제 공개 운영 전에는 입력 처리와 접근 통제를 별도로 검토해야 합니다.
