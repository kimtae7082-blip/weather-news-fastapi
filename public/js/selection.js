

"use strict";



const API = "/api";



const state = {

  regions: [],

  weather: [],

  events: [],

  news: [],

  air: [],

  view: "home",

  regionId: "",

  chart: null,

  climateRequest: 0,

  refreshRequest: 0

};



const $ = (id) => document.getElementById(id);



function createElement(tag, className, text) {

  const element = document.createElement(tag);

  if (className) element.className = className;

  if (text !== undefined) element.textContent = text;

  return element;

}



function clear(element) {

    if (!element) {

        console.error(

            "HTML 요소를 찾을 수 없습니다.",

            new Error().stack

        );

        return false;

    }



    element.replaceChildren();

    return true;

}



function setText(id, value) {

  $(id).textContent = value;

}



function showError(message) {

  const box = $("errorBox");

  box.textContent = message;

  box.classList.remove("hidden");

}



function clearError() {

  $("errorBox").classList.add("hidden");

}



function setLoading(visible) {

  $("loadingBox").classList.toggle("hidden", !visible);

}



function formatNumber(value, digits = 1) {

  if (value === null || value === undefined || value === "") {

    return "-";

  }

  const number = Number(value);

  return Number.isFinite(number) ? number.toFixed(digits) : "-";

}



function formatDate(value) {

  if (!value) return "시간 정보 없음";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return String(value);

  return date.toLocaleString("ko-KR");

}



function regionName(id) {

  const found = state.regions.find(

    (region) => String(region.region_id) === String(id)

  );

  return found ? found.region_name : "선택 지역";

}



function getRegionIdFromName(name) {

  const found = state.regions.find(

    (region) => region.region_name === name

  );

  return found ? String(found.region_id) : null;

}



function matchesRegion(item) {

  if (!state.regionId) return true;



  if (item.region_id !== undefined && item.region_id !== null) {

    return String(item.region_id) === state.regionId;

  }



  if (item.region !== undefined) {

    return getRegionIdFromName(item.region) === state.regionId;

  }



  if (item.region_name !== undefined) {

    return getRegionIdFromName(item.region_name) === state.regionId;

  }



  return false;

}



function filterRegion(items) {

  return items.filter(matchesRegion);

}



async function apiRequest(path, options = {}) {

  const response = await fetch(`${API}${path}`, {

    ...options,

    headers: {

      "Accept": "application/json",

      ...(options.headers || {})

    }

  });



  let result;

  try {

    result = await response.json();

  } catch {

    throw new Error(`서버 응답 오류 (${response.status})`);

  }



  if (!response.ok || result.success === false) {

    const detail = result.detail;

    const message =

      typeof detail === "string"

        ? detail

        : detail?.message || result.message || "요청 실패";

    throw new Error(message);

  }



  return result.data !== undefined ? result.data : result;

}



async function loadRegions() {

  state.regions = await apiRequest("/regions");



  const select = $("regionSelect");

  clear(select);

  select.appendChild(createElement("option", "", "전국 전체"));

  select.firstChild.value = "";



  for (const region of state.regions) {

    const option = createElement(

      "option", "", region.region_name

    );

    option.value = String(region.region_id);

    select.appendChild(option);

  }



  select.value = state.regionId;

}



async function refreshData() {

  const requestId = ++state.refreshRequest;

  clearError();

  setLoading(true);



  try {

    const endpoints = [

      "/weather/observations",

      "/weather/events",

      "/weather-news",

      "/air-quality"

    ];



    const results = await Promise.allSettled(

      endpoints.map((path) => apiRequest(path))

    );



    if (requestId !== state.refreshRequest) return;



    const keys = ["weather", "events", "news", "air"];

    const failures = [];



    results.forEach((result, index) => {

      const key = keys[index];



      if (result.status === "fulfilled") {

        state[key] = Array.isArray(result.value)

          ? result.value

          : [];

      } else {

        state[key] = [];

        failures.push(`${key}: ${result.reason.message}`);

      }

    });



    // 기존 화면 전체 갱신
renderAll();

// 요일별 날씨 + 1시간 간격 예보 갱신
await loadWeatherForecast();


    if (failures.length) {

      showError(

        "일부 데이터를 불러오지 못했습니다. " +

        failures.join(" / ")

      );

    }



    $("liveStatus").textContent =

      failures.length ? "● 일부 데이터 오류" : "● 데이터 연결됨";



    $("liveStatus").classList.toggle(

      "offline", failures.length > 0

    );



  } catch (error) {

    showError(error.message);

    $("liveStatus").textContent = "● 연결 오류";

    $("liveStatus").classList.add("offline");

  } finally {

    if (requestId === state.refreshRequest) {

      setLoading(false);

    }

  }

}



function updateClock() {

  setText(

    "currentTime",

    new Date().toLocaleString("ko-KR", {

      dateStyle: "medium",

      timeStyle: "short"

    })

  );

}



function switchView(view) {

  state.view = view;



  document.querySelectorAll(".view").forEach((element) => {

    element.classList.toggle(

      "hidden",

      element.id !== `${view}View`

    );

  });



  document.querySelectorAll(".nav-link").forEach((button) => {

    button.classList.toggle(

      "active",

      button.dataset.view === view

    );

  });



  const titles = {

    home: ["오늘의 날씨 뉴스",

      "전국 기상 관측 데이터와 최신 날씨 뉴스"],

    weather: ["전국 날씨",

      "지역별 기온, 습도, 풍속 및 강수량"],

    events: ["기상 위험 정보",

      "관측 데이터 기반 자체 기상 위험 분석"],

    climate: ["기후변화 분석",

      "연도별 기온, 강수량 및 폭염일수 비교"]

  };



  setText("pageTitle", titles[view][0]);

  setText("pageDescription", titles[view][1]);



  if (view === "climate") {

    loadClimate();

  }

}



function renderAll() {
  const sections = [
    ["오늘의 날씨", renderTodayWeather],
    ["메인 뉴스", renderHero],
    ["뉴스 목록", renderNews],
    ["전국 날씨", renderWeather],
    ["기상 위험", renderEvents],
    ["위험 요약", renderRiskSummary],
    ["미세먼지", renderAir],
    ["홈 사이드바", renderSidebar],
    ["기상 속보", renderTicker]
  ];

  for (const [name, render] of sections) {
    try {
      render();
    } catch (error) {
      console.error(`${name} 렌더링 실패:`, error);
    }
  }
}

function getSortedNews() {

  return filterRegion(state.news).slice().sort((a, b) => {

    const aDate = new Date(a.created_at || 0).getTime() || 0;

    const bDate = new Date(b.created_at || 0).getTime() || 0;

    return bDate - aDate;

  });

}



function renderHero() {

  const hero = $("heroArticle");

  const overlay = hero.querySelector(".hero-overlay");

  clear(overlay);



  const article = getSortedNews()[0];



  overlay.appendChild(

    createElement("span", "category-label", "TOP WEATHER STORY")

  );



  const title = createElement(

    "h2", "",

    article?.news_title || "오늘의 주요 날씨 뉴스"

  );



  const description = createElement(

    "p", "",

    article

      ? String(article.news_content || "").slice(0, 150)

      : "아직 등록된 날씨 뉴스가 없습니다."

  );



  overlay.append(title, description);



  hero.style.cursor = article ? "pointer" : "default";

  hero.onclick = article ? () => openArticle(article) : null;

}



function renderNews() {

  const container = $("newsList");

  clear(container);



  const news = getSortedNews();



  if (!news.length) {

    container.appendChild(

      createElement(

        "p", "empty-state",

        "선택한 지역에 등록된 날씨 뉴스가 없습니다."

      )

    );

    return;

  }



  for (const article of news) {

    const button = createElement("button", "news-item");

    button.type = "button";



    const category = createElement(

      "span", "news-category",

      article.region || regionName(article.region_id)

    );



    const title = createElement(

      "span", "news-title",

      article.news_title || "제목 없는 뉴스"

    );



    const preview = createElement(

      "span", "news-preview",

      String(article.news_content || "")

        .replace(/\s+/g, " ")

        .slice(0, 180)

    );



    const meta = createElement(

      "span", "news-meta",

      formatDate(article.created_at)

    );



    button.append(category, title, preview, meta);

    button.addEventListener("click", () => openArticle(article));

    container.appendChild(button);

  }

}



function openArticle(article) {

  setText("articleTitle", article.news_title || "날씨 뉴스");



  const region = article.region ||

    regionName(article.region_id);



  setText(

    "articleMeta",

    `${region} · ${formatDate(article.created_at)}`

  );



  setText("articleBody", article.news_content || "");

  $("articleModal").classList.remove("hidden");

  document.body.style.overflow = "hidden";

  $("closeModalButton").focus();

}



function closeArticle() {

  $("articleModal").classList.add("hidden");

  document.body.style.overflow = "";

}



function getLatestWeather() {

  return filterRegion(state.weather);

}



function weatherCard(item) {

  const card = createElement("article", "weather-card");

  const region = createElement(

    "h3", "card-region",

    item.region_name || regionName(item.region_id)

  );



  const value = createElement(

    "div", "card-value",

    `${formatNumber(item.temperature)}℃`

  );



  const details = createElement(

    "div", "card-details",

    `습도 ${formatNumber(item.humidity, 0)}% · ` +

    `풍속 ${formatNumber(item.wind_speed)} km/h`

  );



  details.appendChild(

    createElement(

      "div", "",

      `강수량 ${formatNumber(item.precipitation)} mm`

    )

  );



  card.append(region, value, details);

  return card;

}



function renderWeather() {

  const grid = $("weatherGrid");

  clear(grid);



  const items = getLatestWeather();



  if (!items.length) {

    grid.appendChild(

      createElement("p", "empty-state", "날씨 데이터가 없습니다.")

    );

    return;

  }



  items.forEach((item) => grid.appendChild(weatherCard(item)));

}



function eventCard(item) {

  const card = createElement("article", "event-card");



  const title = createElement(

    "h3", "card-region",

    item.region_name || regionName(item.region_id)

  );



  const severity = createElement(

    "span",

    "severity" +

      (String(item.severity_level || "").includes("경보")

        ? " danger" : ""),

    `${item.event_type || "기상 이벤트"} · ` +

    `${item.severity_level || "주의"}`

  );



  const description = createElement(

    "p", "card-details",

    item.description || "상세 정보가 없습니다."

  );



  card.append(title, severity, description);

  return card;

}



function renderEvents() {

  const grid = $("eventsList");

  clear(grid);



  const items = filterRegion(state.events);



  if (!items.length) {

    grid.appendChild(

      createElement(

        "p", "empty-state",

        "현재 등록된 기상 이벤트가 없습니다."

      )

    );

    return;

  }



  items.forEach((item) => grid.appendChild(eventCard(item)));

}



function airCard(item) {

  const card = createElement("article", "weather-card");



  card.appendChild(

    createElement(

      "h3", "card-region",

      item.region_name || regionName(item.region_id)

    )

  );



  card.appendChild(

    createElement(

      "div", "card-value",

      `${formatNumber(item.pm10, 0)}`

    )

  );



  const details = createElement(

    "div", "card-details",

    "PM10 (㎍/㎥)"

  );



  details.appendChild(

    createElement(

      "div", "",

      `PM2.5: ${formatNumber(item.pm25, 0)} ㎍/㎥`

    )

  );



  details.appendChild(

    createElement(

      "div", "",

      `미세먼지 등급: ${item.pm10_grade ?? "정보 없음"}`

    )

  );



  card.appendChild(details);

  return card;

}



function renderAir() {

    const grid = document.getElementById("airGrid");



    if (!grid) {

        console.error("airGrid HTML 요소가 없습니다.");

        return;

    }



    grid.replaceChildren();



    const items = filterRegion(state.air);



    if (!items.length) {

        grid.appendChild(

            createElement(

                "p",

                "empty-state",

                "미세먼지 데이터가 없습니다."

            )

        );

        return;

    }



    items.forEach((item) => {

        grid.appendChild(airCard(item));

    });

}



function renderSidebar() {

    const weatherBox = $("sidebarWeather");

    const eventsBox = $("sidebarEvents");

    const airBox = $("sidebarAir");



    // HTML 요소 존재 여부 확인

    if (!weatherBox || !eventsBox || !airBox) {

        console.error("사이드바 HTML 요소를 찾을 수 없습니다.", {

            weatherBox,

            eventsBox,

            airBox

        });

        return;

    }



    // 기존 내용 초기화

    clear(weatherBox);

    clear(eventsBox);

    clear(airBox);



    // 1. 현재 날씨 표시

    const current = getLatestWeather()[0];



    if (current) {

        weatherBox.appendChild(

            createElement(

                "div",

                "summary-region",

                current.region_name || regionName(current.region_id)

            )

        );



        weatherBox.appendChild(

            createElement(

                "div",

                "summary-temperature",

                `${formatNumber(current.temperature)}℃`

            )

        );



        const details = createElement("div", "summary-details");



        [

            `습도 ${formatNumber(current.humidity, 0)}%`,

            `풍속 ${formatNumber(current.wind_speed)} km/h`,

            `강수 ${formatNumber(current.precipitation)} mm`,

            `관측 ${formatDate(current.observed_at)}`

        ].forEach(text => {

            details.appendChild(createElement("span", "", text));

        });



        weatherBox.appendChild(details);

    } else {

        weatherBox.appendChild(

            createElement("p", "empty-state", "날씨 정보 없음")

        );

    }



    // 2. 기상 위험 정보 표시

    const events = filterRegion(state.events).slice(0, 4);



    if (!events.length) {

        eventsBox.appendChild(

            createElement(

                "p",

                "empty-state",

                "등록된 기상 위험 정보가 없습니다."

            )

        );

    }



    events.forEach(item => {

        const row = createElement("div", "sidebar-item");



        row.appendChild(

            createElement(

                "strong",

                "",

                `${item.region_name || regionName(item.region_id)} · ${item.event_type || "기상 이벤트"}`

            )

        );



        row.appendChild(

            createElement(

                "span",

                "",

                item.description || ""

            )

        );



        eventsBox.appendChild(row);

    });



    // 3. 미세먼지 정보 표시

    const airItems = filterRegion(state.air).slice(0, 4);



    if (!airItems.length) {

        airBox.appendChild(

            createElement(

                "p",

                "empty-state",

                "대기질 정보 없음"

            )

        );

    }



    airItems.forEach(item => {

        const row = createElement("div", "sidebar-item");



        row.appendChild(

            createElement(

                "strong",

                "",

                item.region_name || regionName(item.region_id)

            )

        );



        row.appendChild(

            createElement(

                "span",

                "",

                `PM10 ${formatNumber(item.pm10, 0)} · PM2.5 ${formatNumber(item.pm25, 0)}`

            )

        );



        airBox.appendChild(row);

    });

}





function renderTicker() {

  const events = filterRegion(state.events);

  const news = getSortedNews();



  if (events.length) {

    const item = events[0];

    setText(

      "tickerText",

      `[자체 기상 분석] ` +

      `${item.region_name || regionName(item.region_id)} · ` +

      `${item.event_type || "기상 위험"} · ` +

      `${item.description || ""}`

    );

  } else if (news.length) {

    setText("tickerText", news[0].news_title);

  } else {

    setText(

      "tickerText",

      "현재 등록된 주요 기상 뉴스가 없습니다."

    );

  }

}



async function generateNews() {

  const regionId = state.regionId;



  if (!regionId) {

    showError(

      "뉴스를 생성하려면 상단에서 지역을 선택해주세요."

    );

    return;

  }



  const button = $("generateNewsButton");

  button.disabled = true;

  button.textContent = "뉴스 생성 중...";

  clearError();



  try {

    const result = await apiRequest(

      `/weather-news/generate/${regionId}`,

      { method: "POST" }

    );



    await refreshData();



    if (result.already_exists) {

      setText(

        "tickerText",

        "해당 관측 데이터의 뉴스가 이미 생성되어 있습니다."

      );

    } else {

      setText(

        "tickerText",

        `${regionName(regionId)} 날씨 뉴스가 생성되었습니다.`

      );

    }



  } catch (error) {

    showError(`뉴스 생성 실패: ${error.message}`);

  } finally {

    button.disabled = false;

    button.textContent = "+ 선택 지역 뉴스 생성";

  }

}



async function loadClimate() {

  const requestId = ++state.climateRequest;



  if (state.chart) {

    state.chart.destroy();

    state.chart = null;

  }



  if (!state.regionId) {

    setText(

      "climateSummary",

      "상단에서 분석할 지역을 먼저 선택해주세요."

    );

    return;

  }



  setText("climateSummary", "기후 데이터를 불러오는 중입니다.");



  try {

    const data = await apiRequest(

      `/climate/analysis/${state.regionId}`

    );



    if (requestId !== state.climateRequest) return;



    const years = Array.isArray(data.years) ? data.years : [];



    if (!years.length) {

      setText("climateSummary", "분석 가능한 기후 데이터가 없습니다.");

      return;

    }



    const chartType = $("chartSelect").value;



    const settings = {

      temperature: {

        field: "avgTemperature",

        label: "연평균 기온 (℃)",

        type: "line"

      },

      rainfall: {

        field: "rainfall",

        label: "연간 강수량 (mm)",

        type: "bar"

      },

      heatwave: {

        field: "heatwaveDays",

        label: "폭염일수 (일)",

        type: "bar"

      }

    };



    const setting = settings[chartType];



    setText(

      "climateSummary",

      `${data.region || regionName(state.regionId)} · ` +

      `${data.period || "연도별 분석"} · ${setting.label}`

    );



    if (typeof Chart === "undefined") {

      throw new Error(

        "Chart.js를 불러오지 못했습니다. 인터넷 연결을 확인하세요."

      );

    }



    const canvas = $("weatherChart");



    state.chart = new Chart(canvas, {

      type: setting.type,

      data: {

        labels: years.map((item) => String(item.year)),

        datasets: [{

          label: setting.label,

          data: years.map((item) => {

            const value = item[setting.field];

            return value == null ? null : Number(value);

          }),

          borderColor: "#38bdf8",

          backgroundColor: "rgba(56,189,248,0.35)",

          pointBackgroundColor: "#7dd3fc",

          borderWidth: 3,

          tension: 0.35,

          fill: setting.type === "line"

        }]

      },

      options: {

        responsive: true,

        maintainAspectRatio: false,

        plugins: {

          legend: {

            labels: { color: "#dbeafe" }

          }

        },

        scales: {

          x: {

            ticks: { color: "#9eafc6" },

            grid: { color: "rgba(148,163,184,.1)" }

          },

          y: {

            ticks: { color: "#9eafc6" },

            grid: { color: "rgba(148,163,184,.15)" }

          }

        }

      }

    });



  } catch (error) {

    if (requestId === state.climateRequest) {

      setText("climateSummary", `기후 분석 오류: ${error.message}`);

    }

  }

}



async function analyzeWeatherRisk() {

    const button = document.getElementById(

        "analyzeWeatherButton"

    );



    button.disabled = true;

    button.textContent = "분석 중...";



    clearError();



    try {

        await apiRequest("/weather/analyze", {

            method: "POST"

        });



        await refreshData();



        setText(

            "tickerText",

            "기상 위험 분석이 완료되었습니다."

        );



    } catch (error) {

        showError(

            "기상 위험 분석 실패: " + error.message

        );

    } finally {

        button.disabled = false;

        button.textContent = "⚠ 기상 위험 다시 분석";

    }

}



function renderRiskSummary() {

    const container = document.getElementById("riskSummary");



    if (!container) {

        console.warn("riskSummary 요소가 없습니다.");

        return;

    }



    container.replaceChildren();



    const events = filterRegion(state.events);



    const warningCount = events.filter(

        item => String(item.severity_level || "").includes("경보")

    ).length;



    const cautionCount = events.filter(

        item => String(item.severity_level || "").includes("주의")

    ).length;



    const summaries = [

        { label: "전체 위험 이벤트", count: events.length },

        { label: "경보 수준", count: warningCount },

        { label: "주의 수준", count: cautionCount }

    ];



    summaries.forEach(item => {

        const card = document.createElement("div");

        card.className = "risk-summary-card";



        const label = document.createElement("span");

        label.textContent = item.label;



        const count = document.createElement("strong");

        count.textContent = item.count;



        card.append(label, count);

        container.appendChild(card);

    });

}



async function initialize() {

  updateClock();



  document.querySelectorAll(".nav-link").forEach((button) => {

    button.addEventListener("click", () => {

      switchView(button.dataset.view);

    });

  });



  $("regionSelect").addEventListener("change", async (event) => {

    state.regionId = event.target.value;

    state.climateRequest++;

    renderAll();

  // 선택 지역의 요일별·시간별 예보 갱신
    await loadWeatherForecast();

    if (state.view === "climate") {

      loadClimate();

    }

  });



  $("chartSelect").addEventListener("change", loadClimate);



  $("refreshButton").addEventListener("click", refreshData);



  $("generateNewsButton").addEventListener(

    "click", generateNews

  );



  $("closeModalButton").addEventListener(

    "click", closeArticle

  );



 const analyzeButton = document.getElementById(

    "analyzeWeatherButton"

);



if (analyzeButton) {

    analyzeButton.addEventListener(

        "click",

        analyzeWeatherRisk

    );

}



  document.querySelectorAll("[data-close-modal]").forEach(

    (element) => element.addEventListener("click", closeArticle)

  );



  document.addEventListener("keydown", (event) => {

    if (event.key === "Escape") closeArticle();

  });



  switchView("home");



  try {

    await loadRegions();

  } catch (error) {

    showError(`지역 목록 조회 실패: ${error.message}`);

  }



  await refreshData();

}



function renderTodayWeather() {

    const container = document.getElementById("todayWeather");



    if (!container) return;



    const items = filterRegion(state.weather);

    const weather = items[0];



    container.replaceChildren();



    if (!weather) {

        container.textContent = "현재 날씨 정보가 없습니다.";

        return;

    }



    const title = document.createElement("h3");

    title.textContent = weather.region_name || "선택 지역";



    const temperature = document.createElement("h2");

    temperature.textContent = `${weather.temperature}℃`;



    const details = document.createElement("p");

    details.textContent =

        `습도 ${weather.humidity}% · ` +

        `풍속 ${weather.wind_speed} km/h · ` +

        `강수량 ${weather.precipitation ?? 0} mm`;



    const updated = document.createElement("p");

    updated.className = "section-note";

    updated.textContent =

        `관측 시각: ${weather.observed_at || "확인 중"}`;



    container.append(title, temperature, details, updated);

}

// 요일을 한국어로 표시하기 위한 배열
const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

// 날씨 코드에 따라 아이콘을 결정하는 함수
function getWeatherIcon(code) {
    if (code === 0) return "☀️";
    if ([1, 2].includes(code)) return "🌤️";
    if (code === 3) return "☁️";
    if ([45, 48].includes(code)) return "🌫️";
    if ([51, 53, 55, 61, 63, 65, 80, 81, 82].includes(code)) {
        return "🌧️";
    }
    if ([71, 73, 75, 77, 85, 86].includes(code)) return "❄️";
    if ([95, 96, 99].includes(code)) return "⛈️";
    return "🌥️";
}


// 전국 17개 시·도 대표 좌표
// 각 지역 전체가 아닌 대표 지점의 날씨를 조회합니다.
const REGION_COORDINATES = {
    seoul: [37.5665, 126.9780],
    busan: [35.1796, 129.0756],
    daegu: [35.8714, 128.6014],
    incheon: [37.4563, 126.7052],
    gwangju: [35.1595, 126.8526],
    daejeon: [36.3504, 127.3845],
    ulsan: [35.5384, 129.3114],
    sejong: [36.4800, 127.2890],
    gyeonggi: [37.4138, 127.5183],
    gangwon: [37.8228, 128.1555],
    chungbuk: [36.8000, 127.7000],
    chungnam: [36.5184, 126.8000],
    jeonbuk: [35.8203, 127.1089],
    jeonnam: [34.8679, 126.9910],
    gyeongbuk: [36.4919, 128.8889],
    gyeongnam: [35.4606, 128.2132],
    jeju: [33.4996, 126.5312]
};

// 선택한 지역의 요일별·시간별 날씨 예보 조회
async function loadWeatherForecast() {

    const weeklyBox = document.getElementById("weeklyForecast");
    const hourlyBox = document.getElementById("hourlyForecast");

    // HTML에 예보 영역이 없으면 종료
    if (!weeklyBox || !hourlyBox) return;

    weeklyBox.textContent = "요일별 예보를 불러오는 중...";
    hourlyBox.textContent = "시간별 예보를 불러오는 중...";

    try {
        // 지역 목록 확인
        const regions = Array.isArray(state.regions)
            ? state.regions
            : [];

        // 선택한 지역 찾기
        const region = regions.find(
            item => String(item.region_id) === String(state.regionId)
        ) || regions.find(
            item => item.city_code === "seoul"
        );

        if (!region) {
            throw new Error("지역 데이터를 찾을 수 없습니다.");
        }

        // 지역 코드로 대표 좌표 가져오기
        const coordinates = REGION_COORDINATES[region.city_code];

        if (!coordinates) {
            throw new Error(
                `${region.city_code} 지역의 좌표가 없습니다.`
            );
        }

        // 위도와 경도는 여기서 한 번만 선언
        const [latitude, longitude] = coordinates;

        console.log("선택 지역:", region.city_code);
        console.log("위도:", latitude);
        console.log("경도:", longitude);

        // Open-Meteo API 주소 생성
        const url = new URL(
            "https://api.open-meteo.com/v1/forecast"
        );

        url.searchParams.set("latitude", latitude);
        url.searchParams.set("longitude", longitude);
        url.searchParams.set("timezone", "Asia/Seoul");
        url.searchParams.set("forecast_days", "7");

        // 시간별 날씨
        url.searchParams.set(
            "hourly",
            "temperature_2m,precipitation_probability,weather_code"
        );

        // 요일별 날씨
        url.searchParams.set(
            "daily",
            "temperature_2m_max,temperature_2m_min,weather_code"
        );

        console.log("예보 API 주소:", url.toString());

        // API 요청
        const response = await fetch(url.toString());

        if (!response.ok) {
            const errorText = await response.text();

            throw new Error(
                `날씨 API 오류 (${response.status}): ${errorText}`
            );
        }

        // JSON 데이터 변환
        const data = await response.json();

        console.log("예보 데이터:", data);

        // 응답 데이터 확인
        if (!data.daily || !data.hourly) {
            throw new Error("예보 데이터가 없습니다.");
        }

        // 요일별 예보 출력
        renderWeeklyForecast(data.daily);

        // 시간별 예보 출력
        renderHourlyForecast(data.hourly);

    } catch (error) {

        console.error("날씨 예보 조회 실패:", error);

        weeklyBox.textContent =
            "요일별 예보를 불러오지 못했습니다.";

        hourlyBox.textContent =
            "시간별 예보를 불러오지 못했습니다.";
    }
}


// 일주일 예보를 화면에 표시
function renderWeeklyForecast(daily) {
    const box = document.getElementById("weeklyForecast");
    box.replaceChildren();

    daily.time.forEach((dateString, index) => {
        // API의 날짜 문자열을 이용해 요일 계산
        const date = new Date(`${dateString}T12:00:00`);
        const weekday = WEEKDAYS[date.getDay()];

        const card = document.createElement("div");
        card.className = "forecast-card";

        const day = document.createElement("strong");
        day.textContent = `${weekday} (${dateString.slice(5)})`;

        const icon = document.createElement("div");
        icon.className = "forecast-icon";
        icon.textContent = getWeatherIcon(daily.weather_code[index]);

        const temperature = document.createElement("span");
        temperature.textContent =
            `${daily.temperature_2m_min[index]}° / ` +
            `${daily.temperature_2m_max[index]}°`;

        card.append(day, icon, temperature);
        box.appendChild(card);
    });
}

// 현재 시간부터 1시간 간격으로 12시간 예보 표시
function renderHourlyForecast(hourly) {
    const box = document.getElementById("hourlyForecast");
    box.replaceChildren();

    // 한국 시간 기준 현재 날짜 및 시간 문자열
    const nowKorea = new Intl.DateTimeFormat("sv-SE", {
        timeZone: "Asia/Seoul",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        hourCycle: "h23"
    }).format(new Date()).replace(" ", "T");

    // 현재 시간 이상인 첫 예보 찾기
    const startIndex = hourly.time.findIndex(
        time => time >= nowKorea.slice(0, 13)
    );

    if (startIndex === -1) {
        box.textContent = "표시할 시간별 예보가 없습니다.";
        return;
    }

    const endIndex = Math.min(startIndex + 12, hourly.time.length);

    for (let i = startIndex; i < endIndex; i++) {
        const card = document.createElement("div");
        card.className = "forecast-card";

        const time = document.createElement("strong");
        time.textContent = `${hourly.time[i].slice(11, 13)}시`;

        const icon = document.createElement("div");
        icon.className = "forecast-icon";
        icon.textContent = getWeatherIcon(hourly.weather_code[i]);

        const temperature = document.createElement("span");
        temperature.textContent = `${hourly.temperature_2m[i]}℃`;

        const rain = document.createElement("small");
        rain.textContent =
            `강수확률 ${hourly.precipitation_probability[i] ?? "-"}%`;

        card.append(time, icon, temperature, rain);
        box.appendChild(card);
    }
}

document.addEventListener("DOMContentLoaded", initialize);



// 5분마다 최신 날씨 및 대기질 데이터 조회

setInterval(() => {

    refreshData();

}, 5 * 60 * 1000);
