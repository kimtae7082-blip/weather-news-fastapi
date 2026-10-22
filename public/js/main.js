// HTML 요소를 모두 읽은 뒤 버튼을 연결하고 최초 데이터를 조회합니다.
document.addEventListener('DOMContentLoaded', () => {

    const refreshButton =
        document.getElementById('btnRefresh');

    refreshButton.addEventListener(
        'click',
        loadDashboardData
    );

    loadDashboardData();
    
});


/*
=========================================================
전체 대시보드 데이터 로딩
=========================================================
*/

// 조회 순서: 저장된 관측 → 이벤트 → 뉴스 → 외부 대기질 → 기후 분석입니다.
// 새로고침 버튼은 조회만 하며 날씨 수집·이벤트 분석·뉴스 생성 POST는 호출하지 않습니다.
async function loadDashboardData() {
    showLoading(true);
    hideError();

    try {
        // 저장된 날씨 데이터 먼저 조회
        const observationsRes = await fetchAPI(
            '/api/weather/observations'
        );

        const observations = observationsRes.data || [];

        // 날씨 화면 표시
        renderNationalWeather(observations);
        renderMajorRegions(observations);

        // 기상 이벤트는 별도로 조회
        try {
            const eventsRes = await fetchAPI(
                '/api/weather/events'
            );

            const events = eventsRes.data || [];

            renderWarnings(events);
            renderWeatherEvents(events);

        } catch (error) {
            console.error('기상 이벤트 조회 실패:', error);
            renderWarnings([]);
            renderWeatherEvents([]);
        }

        // 뉴스도 별도로 조회
        try {
            const newsRes = await fetchAPI(
                '/api/weather-news'
            );

            renderTodayNews(newsRes.data || []);

        } catch (error) {
            console.error('뉴스 조회 실패:', error);
            renderTodayNews([]);
        }
    
        renderDustStatus();
        renderClimateChange();
        
        await loadAirQuality();
        
        // 기후변화 분석 추가
        await loadClimateAnalysis(1);

    } catch (error) {
        console.error('날씨 조회 실패:', error);
        showError(error.message);

    } finally {
        showLoading(false);
    }
}


/*
=========================================================
API 공통 함수
=========================================================
*/

// HTTP 상태와 JSON의 success를 모두 확인하는 공통 요청 함수입니다.
async function fetchAPI(url, options = {}) {

    const response =
        await fetch(url, options);

    if (!response.ok) {

        throw new Error(
            `서버 응답 오류: ${response.status}`
        );
    }

    const result =
        await response.json();

    if (!result.success) {

        throw new Error(
            result.message ||
            '데이터를 불러오지 못했습니다.'
        );
    }

    return result;
}


/*
=========================================================
전국 평균 날씨
=========================================================
*/

// 조회된 대표 지점들의 단순 평균입니다. 면적·인구 가중 전국 평균은 아닙니다.
function renderNationalWeather(
    observations
) {

    const container =
        document.getElementById(
            'nationalWeatherSummary'
        );

    if (
        !observations ||
        observations.length === 0
    ) {

        container.innerHTML =
            '<p class="text-muted">관측 데이터가 없습니다.</p>';

        return;
    }


    const temperatures =
        observations.map(
            item => Number(item.temperature)
        );

    const avgTemp =
        (
            temperatures.reduce(
                (sum, value) => sum + value,
                0
            ) / temperatures.length
        ).toFixed(1);


    const maxTempObs =
        observations.reduce(
            (prev, current) =>
                Number(prev.temperature) >
                Number(current.temperature)
                    ? prev
                    : current
        );


    const minTempObs =
        observations.reduce(
            (prev, current) =>
                Number(prev.temperature) <
                Number(current.temperature)
                    ? prev
                    : current
        );


    container.innerHTML = `

        <div class="col-md-4 mb-3">

            <div class="summary-box">

                <small>
                    전국 평균 기온
                </small>

                <strong class="text-primary">
                    ${avgTemp}℃
                </strong>

            </div>

        </div>


        <div class="col-md-4 mb-3">

            <div class="summary-box">

                <small>
                    최고 기온
                </small>

                <strong class="text-danger">
                    ${maxTempObs.region_name}
                    ${maxTempObs.temperature}℃
                </strong>

            </div>

        </div>


        <div class="col-md-4 mb-3">

            <div class="summary-box">

                <small>
                    최저 기온
                </small>

                <strong class="text-info">
                    ${minTempObs.region_name}
                    ${minTempObs.temperature}℃
                </strong>

            </div>

        </div>

    `;
}


/*
=========================================================
17개 시·도 날씨
=========================================================
*/

let selectedWeatherRegionId = null;

// 최신 관측을 보관해 두고 지역 버튼을 누를 때 해당 지역의 상세값을 찾습니다.
function renderMajorRegions(observations) {
    const container =
        document.getElementById('majorRegionsTable');

    if (!container) return;

    // 기존 데이터 보관
    window.currentWeatherObservations = observations;

    // 테이블 내부에 지역 선택 버튼과 상세정보 영역 생성
    container.innerHTML = `
        <tr>
            <td colspan="6">
                <div id="weatherRegionButtons"
                     class="d-flex flex-wrap gap-2 mb-3">
                </div>
                <div id="selectedWeatherDetail"></div>
            </td>
        </tr>
    `;

    const buttonContainer =
        document.getElementById('weatherRegionButtons');

    observations.forEach(region => {
        const button = document.createElement('button');

        button.type = 'button';
        button.className = 'btn btn-outline-primary btn-sm';
        button.textContent = region.region_name;

        button.addEventListener('click', () => {
            showSelectedWeather(region.region_id);
        });

        buttonContainer.appendChild(button);
    });

    const initialRegion = observations.find(
        r => String(r.region_id) === String(selectedWeatherRegionId)
    ) || observations[0];

    if (initialRegion) {
        showSelectedWeather(initialRegion.region_id);
    }
}

// DB 관측과 외부 대기질을 region_id로 연결합니다.
// String으로 비교해 숫자 1과 문자열 '1'의 자료형 차이를 처리합니다.
function showSelectedWeather(regionId) {
    const observations =
        window.currentWeatherObservations || [];

    const region = observations.find(
        item => String(item.region_id) === String(regionId)
    );

    if (!region) return;

    selectedWeatherRegionId = regionId;

    const detail =
        document.getElementById('selectedWeatherDetail');

    if (!detail) return;

    document.querySelectorAll('#weatherRegionButtons button')
        .forEach((button, index) => {
            const selected =
                String(observations[index].region_id) === String(regionId);

            button.className = selected
                ? 'btn btn-primary btn-sm'
                : 'btn btn-outline-primary btn-sm';
        });

    // 기존 미세먼지 데이터와 지역 ID로 연결
    const dust = (typeof airQualityData !== 'undefined'
        ? airQualityData : []).find(
            item => String(item.region_id) === String(regionId)
        );

    detail.innerHTML = `
        <div class="card shadow-sm p-3">
            <h5 id="weatherDetailRegion"></h5>

            <div class="row g-3 mt-2">
                <div class="col-md-4">
                    <div class="border rounded p-3">
                        <h6>현재 기온</h6>
                        <h3 id="weatherDetailTemp"></h3>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="border rounded p-3">
                        <h6>습도</h6>
                        <h3 id="weatherDetailHumidity"></h3>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="border rounded p-3">
                        <h6>풍속</h6>
                        <h3 id="weatherDetailWind"></h3>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="border rounded p-3">
                        <h6>강수량</h6>
                        <h3 id="weatherDetailRain"></h3>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="border rounded p-3">
                        <h6>미세먼지 PM10</h6>
                        <h3 id="weatherDetailPm10"></h3>
                        <strong id="weatherDetailPm10Grade"></strong>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="border rounded p-3">
                        <h6>초미세먼지 PM2.5</h6>
                        <h3 id="weatherDetailPm25"></h3>
                        <strong id="weatherDetailPm25Grade"></strong>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('weatherDetailRegion')
        .textContent = region.region_name;

    document.getElementById('weatherDetailTemp')
        .textContent = `${region.temperature ?? '-'} ℃`;

    document.getElementById('weatherDetailHumidity')
        .textContent = `${region.humidity ?? '-'} %`;

    document.getElementById('weatherDetailWind')
        .textContent = `${region.wind_speed ?? '-'} km/h`;

    document.getElementById('weatherDetailRain')
        .textContent = `${region.precipitation ?? '-'} mm`;

    document.getElementById('weatherDetailPm10')
        .textContent = `${dust?.pm10 ?? '-'} ㎍/㎥`;

    document.getElementById('weatherDetailPm25')
        .textContent = `${dust?.pm25 ?? '-'} ㎍/㎥`;

    document.getElementById('weatherDetailPm10Grade')
        .textContent = dust?.pm10_grade ?? '정보 없음';

    document.getElementById('weatherDetailPm25Grade')
        .textContent = dust?.pm25_grade ?? '정보 없음';
}


/*
=========================================================
기상특보 / 이벤트
=========================================================
*/

// 화면의 '경보'는 자체 규칙의 결과이며 공식 기상특보 발표를 뜻하지 않습니다.
function renderWarnings(events) {

    const list =
        document.getElementById(
            'warningsList'
        );

    list.innerHTML = '';


    if (
        !events ||
        events.length === 0
    ) {

        list.innerHTML = `
            <li class="list-group-item text-muted">
                현재 감지된 특이 기상 현상이 없습니다.
            </li>
        `;

        return;
    }


    events.forEach(event => {

        const li =
            document.createElement('li');

        const badgeClass =
            event.severity_level === '경보'
                ? 'bg-danger'
                : 'bg-warning text-dark';


        li.className =
            'list-group-item d-flex justify-content-between align-items-start';


        li.innerHTML = `

            <div class="ms-2 me-auto">

                <div class="fw-bold">
                    ${event.region_name}
                    -
                    ${event.event_type}
                </div>

                <small class="text-secondary">
                    ${event.description}
                </small>

            </div>

            <span class="badge ${badgeClass} rounded-pill">
                ${event.severity_level}
            </span>

        `;

        list.appendChild(li);
    });
}


/*
=========================================================
기상 이벤트 카드
=========================================================
*/

function renderWeatherEvents(events) {

    const container =
        document.getElementById(
            'weatherEventsContainer'
        );

    container.innerHTML = '';


    if (
        !events ||
        events.length === 0
    ) {

        container.innerHTML =
            '<p class="text-muted">현재 특별한 기상 현상이 없습니다.</p>';

        return;
    }


    events.forEach(event => {

        const card =
            document.createElement('div');

        card.className =
            'event-card';


        card.innerHTML = `

            <span class="badge bg-secondary">
                ${event.region_name}
            </span>

            <strong>
                ${event.event_type}
            </strong>

            <small>
                ${event.description}
            </small>

        `;

        container.appendChild(card);
    });
}


/*
=========================================================
미세먼지
=========================================================
*/

// 이전 안내용 함수입니다. 현재 대시보드에서는 loadAirQuality 경로를 사용합니다.
function renderDustStatus() {

    const container =
        document.getElementById(
            'dustStatusContainer'
        );

    container.innerHTML = `

        <div class="col-12">

            <div class="alert alert-info mb-0">

                <strong>
                    미세먼지 데이터
                </strong>

                <br>

                현재 날씨 데이터에는
                미세먼지 정보가 포함되어 있지 않습니다.

                실제 PM10 / PM2.5 데이터를 표시하려면
                별도의 대기질 API 연동이 필요합니다.

            </div>

        </div>

    `;
}


/*
=========================================================
오늘의 날씨 뉴스
=========================================================
*/

// 뉴스는 최대 5개만 표시합니다. 날짜 표시에는 브라우저의 시간대가 반영됩니다.
// 기존 innerHTML에 넣는 기사 문자열은 신뢰된 입력이라는 전제입니다. 외부 입력은 별도 검수가 필요합니다.
function renderTodayNews(newsList) {

    const container =
        document.getElementById(
            'todayNewsContainer'
        );

    container.innerHTML = '';


    if (
        !newsList ||
        newsList.length === 0
    ) {

        container.innerHTML =
            '<p class="text-muted">등록된 날씨 뉴스가 없습니다.</p>';

        return;
    }


    newsList.slice(0, 5).forEach(news => {

        const item =
            document.createElement('div');

        item.className =
            'news-item';


        const date =
            news.created_at
                ? new Date(
                    news.created_at
                ).toLocaleDateString('ko-KR')
                : '';


        item.innerHTML = `

            <div class="d-flex justify-content-between">

                <span class="badge bg-info text-dark">
                    ${news.region}
                </span>

                <small class="text-muted">
                    ${date}
                </small>

            </div>

            <h6 class="fw-bold mt-2">
                ${news.news_title}
            </h6>

            <p class="small text-secondary mb-0">
                ${news.news_content}
            </p>

        `;

        container.appendChild(item);
    });
}


/*
=========================================================
기후변화 안내
=========================================================
*/

// 이전 안내용 함수입니다. 현재 기후 수치는 loadClimateAnalysis 경로에서 받습니다.
function renderClimateChange() {

    const container =
        document.getElementById(
            'climateChangeContainer'
        );

    container.innerHTML = `

        <div class="alert alert-success mb-0">

            <h6 class="fw-bold">
                🌡️ 기후변화 분석
            </h6>

            <p class="small mb-0">

                현재 데이터베이스에는
                장기간 기후 관측 데이터가 별도로 저장되어 있지 않습니다.

                따라서 현재 화면에서는
                실시간 날씨와 기상 이벤트를 중심으로 제공합니다.

                향후 연도별 평균기온,
                강수량,
                폭염일수 등의 데이터를 축적하면
                장기 기후변화 분석 기능을 추가할 수 있습니다.

            </p>

        </div>

    `;
}


/*
=========================================================
로딩
=========================================================
*/

function showLoading(isLoading) {

    const spinner =
        document.getElementById(
            'loadingSpinner'
        );

    if (isLoading) {

        spinner.classList.remove(
            'd-none'
        );

    } else {

        spinner.classList.add(
            'd-none'
        );
    }
}


/*
=========================================================
에러
=========================================================
*/

function showError(message) {

    const errorBox =
        document.getElementById(
            'errorMessage'
        );

    const errorText =
        document.getElementById(
            'errorText'
        );

    errorText.textContent =
        message;

    errorBox.classList.remove(
        'd-none'
    );
}


function hideError() {

    const errorBox =
        document.getElementById(
            'errorMessage'
        );

    errorBox.classList.add(
        'd-none'
    );
}

let airQualityData = [];

// 미세먼지 API에서 전국 데이터 가져오기
// 대기질 조회가 끝나야 지역별 날씨 상세에서도 미세먼지를 함께 표시할 수 있습니다.
async function loadAirQuality() {
    const response = await fetch('/api/air-quality');

    if (!response.ok) {
        throw new Error('미세먼지 API 연결 실패');
    }

    const result = await response.json();

    if (!result.success) {
        throw new Error('미세먼지 조회 실패');
    }

    airQualityData = result.data;

    renderAirQualitySelector();
}

// 지역 선택 버튼 만들기
function renderAirQualitySelector() {
    const container =
        document.getElementById('dustStatusContainer');

    if (!container) return;

    container.innerHTML = `
        <div class="mb-3">
            <h5>지역별 미세먼지 정보</h5>
            <div id="regionButtons"
                 class="d-flex flex-wrap gap-2"></div>
        </div>

        <div id="selectedAirQuality"></div>
    `;

    const buttonContainer =
        document.getElementById('regionButtons');

    airQualityData.forEach(region => {
        const button = document.createElement('button');

        button.type = 'button';
        button.className =
            'btn btn-outline-primary btn-sm';

        button.textContent = region.region_name;

        button.addEventListener('click', () => {
            showSelectedAirQuality(region.region_id);
        });

        buttonContainer.appendChild(button);
    });

    // 처음 화면에 서울 표시
    const initialRegion =
        airQualityData.find(r => r.region_name.includes('서울'))
        || airQualityData[0];

    if (initialRegion) {
        showSelectedAirQuality(initialRegion.region_id);
    }
}

// 선택한 지역의 미세먼지 표시
// 지역별 error를 먼저 확인합니다. 결측 수치는 ??로 '-'를 표시하므로 실제 0은 유지합니다.
function showSelectedAirQuality(regionId) {
    const region = airQualityData.find(
        item => String(item.region_id) === String(regionId)
    );

    if (!region) return;

    const container =
        document.getElementById('selectedAirQuality');

    if (!container) return;

    // 버튼 선택 상태 표시
    document.querySelectorAll('#regionButtons button')
        .forEach((button, index) => {
            const selected =
                String(airQualityData[index].region_id)
                === String(regionId);

            button.className = selected
                ? 'btn btn-primary btn-sm'
                : 'btn btn-outline-primary btn-sm';
        });

    // API 조회 실패한 지역 처리
    if (region.error) {
        container.textContent =
            `${region.region_name}: 미세먼지 정보를 가져올 수 없습니다.`;
        return;
    }

    const getGradeColor = grade => {
        switch (grade) {
            case '좋음': return 'text-primary';
            case '보통': return 'text-success';
            case '나쁨': return 'text-warning';
            case '매우 나쁨': return 'text-danger';
            default: return 'text-secondary';
        }
    };

    // 안전하게 텍스트로 삽입
    container.innerHTML = `
        <div class="card shadow-sm p-3">
            <h5 id="dustRegionName"></h5>

            <div class="row g-3 mt-1">
                <div class="col-md-6">
                    <div class="border rounded p-3">
                        <h6>미세먼지 (PM10)</h6>
                        <h3 id="pm10Value"></h3>
                        <strong id="pm10Grade"
                            class="${getGradeColor(region.pm10_grade)}">
                        </strong>
                    </div>
                </div>

                <div class="col-md-6">
                    <div class="border rounded p-3">
                        <h6>초미세먼지 (PM2.5)</h6>
                        <h3 id="pm25Value"></h3>
                        <strong id="pm25Grade"
                            class="${getGradeColor(region.pm25_grade)}">
                        </strong>
                    </div>
                </div>
            </div>

            <small id="dustObservedAt"
                class="text-muted mt-3"></small>
        </div>
    `;

    document.getElementById('dustRegionName')
        .textContent = region.region_name;

    document.getElementById('pm10Value')
        .textContent = `${region.pm10 ?? '-'} ㎍/㎥`;

    document.getElementById('pm25Value')
        .textContent = `${region.pm25 ?? '-'} ㎍/㎥`;

    document.getElementById('pm10Grade')
        .textContent = region.pm10_grade ?? '정보 없음';

    document.getElementById('pm25Grade')
        .textContent = region.pm25_grade ?? '정보 없음';

    document.getElementById('dustObservedAt')
        .textContent =
            `데이터 기준 시각: ${region.observed_at ?? '정보 없음'}`;
}

let selectedClimateRegionId = 1;

// 지역을 바꿀 때 과거 자료를 다시 요청합니다. 외부 API 응답에 따라 시간이 걸립니다.
async function loadClimateAnalysis(regionId = 1) {
    const container =
        document.getElementById('climateChangeContainer');

    if (!container) return;

    selectedClimateRegionId = regionId;
    container.textContent = '기후변화 데이터 분석 중...';

    try {
        const response = await fetch(
            `/api/climate/analysis/${regionId}`
        );

        if (!response.ok) {
            throw new Error('기후 분석 API 오류');
        }

        const result = await response.json();

        if (!result.success) {
            throw new Error('기후 분석 실패');
        }

        renderClimateAnalysis(result.data);

    } catch (error) {
        console.error(error);
        container.textContent =
            '기후변화 분석 데이터를 불러올 수 없습니다.';
    }
}

// 연도별 집계와 첫해·마지막 해 차이를 표시합니다. 장기 추세 검정 결과가 아닙니다.
function renderClimateAnalysis(data) {
    const container =
        document.getElementById('climateChangeContainer');

    const diff = data.comparison;

    container.innerHTML = `
        <div class="card p-3 shadow-sm">
            <h5 id="climateRegionTitle"></h5>
            <p class="text-muted" id="climatePeriod"></p>

            <div class="row g-3">
                <div class="col-md-4">
                    <div class="border rounded p-3">
                        <h6>평균기온 차이</h6>
                        <h3 id="climateTempDiff"></h3>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="border rounded p-3">
                        <h6>연간 강수량 차이</h6>
                        <h3 id="climateRainDiff"></h3>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="border rounded p-3">
                        <h6>폭염일수 차이</h6>
                        <h3 id="climateHeatDiff"></h3>
                    </div>
                </div>
            </div>

            <h6 class="mt-4">연도별 평균기온</h6>
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>연도</th>
                            <th>평균기온</th>
                            <th>강수량</th>
                            <th>폭염일수</th>
                        </tr>
                    </thead>
                    <tbody id="climateYearTable"></tbody>
                </table>
            </div>
        </div>
    `;

    document.getElementById('climateRegionTitle')
        .textContent = `${data.region} 기후변화 분석`;

    document.getElementById('climatePeriod')
        .textContent = `분석 기간: ${data.period}`;

    document.getElementById('climateTempDiff')
        .textContent =
            `${diff.temperatureDifference ?? '-'} ℃`;

    document.getElementById('climateRainDiff')
        .textContent =
            `${diff.rainfallDifference ?? '-'} mm`;

    document.getElementById('climateHeatDiff')
        .textContent =
            `${diff.heatwaveDaysDifference ?? '-'} 일`;

    const tbody = document.getElementById('climateYearTable');

    data.years.forEach(year => {
        const row = document.createElement('tr');

        [
            year.year,
            year.avgTemperature == null
                ? '-'
                : `${year.avgTemperature} ℃`,
            `${year.rainfall} mm`,
            `${year.heatwaveDays} 일`
        ].forEach(value => {
            const cell = document.createElement('td');
            cell.textContent = value;
            row.appendChild(cell);
        });

        tbody.appendChild(row);
    });
}

// FastAPI 기후 지역 선택 기능
async function initClimateRegionSelector() {
    const container = document.getElementById('climateChangeContainer');
    if (!container) return;
    const res = await fetch('/api/regions');
    if (!res.ok) throw new Error('지역 목록 조회 실패');
    const payload = await res.json();
    container.innerHTML = '<div id="climateRegionButtons" class="d-flex flex-wrap gap-2 mb-3"></div><div id="climateAnalysisResult"></div>';
    const buttons = document.getElementById('climateRegionButtons');
    for (const r of payload.data) {
        const b = document.createElement('button');
        b.className='btn btn-outline-primary btn-sm'; b.textContent=r.region_name; b.type='button';
        b.addEventListener('click',()=>{
            buttons.querySelectorAll('button').forEach(x=>x.className='btn btn-outline-primary btn-sm');
            b.className='btn btn-primary btn-sm';
            loadClimateAnalysis(r.region_id);
        });
        buttons.appendChild(b);
    }
    if(buttons.firstChild) buttons.firstChild.click();
}
