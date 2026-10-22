
-- =====================================================
-- 전국 날씨 뉴스 앱 통합 스키마
-- MySQL 8.0+
-- 기존 데이터 삭제 없음
-- 외래키 자료형 자동 일치
-- =====================================================

CREATE DATABASE IF NOT EXISTS weather_korea
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE weather_korea;

-- =====================================================
-- 1. 지역 테이블
-- =====================================================

CREATE TABLE IF NOT EXISTS region (
    region_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    city_code VARCHAR(50) NOT NULL UNIQUE,
    region_name VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =====================================================
-- 2. 전국 17개 시·도 등록
-- 기존 city_code가 있으면 중복 삽입하지 않음
-- =====================================================

INSERT IGNORE INTO region (city_code, region_name)
VALUES
('seoul', '서울'),
('busan', '부산'),
('daegu', '대구'),
('incheon', '인천'),
('gwangju', '광주'),
('daejeon', '대전'),
('ulsan', '울산'),
('sejong', '세종'),
('gyeonggi', '경기'),
('gangwon', '강원'),
('chungbuk', '충북'),
('chungnam', '충남'),
('jeonbuk', '전북'),
('jeonnam', '전남'),
('gyeongbuk', '경북'),
('gyeongnam', '경남'),
('jeju', '제주');


-- =====================================================
-- 3. 기존 region.region_id 자료형 확인
-- =====================================================

SELECT COLUMN_TYPE INTO @region_id_type
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'weather_korea'
  AND TABLE_NAME = 'region'
  AND COLUMN_NAME = 'region_id';

SELECT @region_id_type AS region_id_type;


-- =====================================================
-- 4. 날씨 관측 테이블
-- region_id 자료형 자동 일치
-- =====================================================

SET @sql = CONCAT(
'CREATE TABLE IF NOT EXISTS weather_observation (
    observation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    region_id ', @region_id_type, ' NOT NULL,
    temperature DECIMAL(5,2) NOT NULL,
    humidity INT NOT NULL,
    wind_speed DECIMAL(6,2) NOT NULL,
    precipitation DECIMAL(5,1) DEFAULT 0.0,
    weather_code INT NOT NULL DEFAULT 0,
    observed_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_observation_region
        FOREIGN KEY (region_id)
        REFERENCES region(region_id)
        ON DELETE CASCADE,

    UNIQUE KEY uk_region_observed
        (region_id, observed_at),

    INDEX idx_observed_at (observed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- =====================================================
-- 5. 기존 관측 테이블의 실제 자료형 확인
-- =====================================================

SELECT COLUMN_TYPE INTO @observation_id_type
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'weather_korea'
  AND TABLE_NAME = 'weather_observation'
  AND COLUMN_NAME = 'observation_id';

SELECT
    @region_id_type AS region_id_type,
    @observation_id_type AS observation_id_type;


-- =====================================================
-- 6. 기상 이벤트 테이블
-- Error Code 3780 방지
-- =====================================================

SET @sql = CONCAT(
'CREATE TABLE IF NOT EXISTS weather_event (
    event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    observation_id ', @observation_id_type, ' NOT NULL,
    region_id ', @region_id_type, ' NOT NULL,

    event_type VARCHAR(50) NOT NULL,
    severity_level VARCHAR(20) NOT NULL DEFAULT ''주의'',
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_event_observation
        FOREIGN KEY (observation_id)
        REFERENCES weather_observation(observation_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_event_region
        FOREIGN KEY (region_id)
        REFERENCES region(region_id)
        ON DELETE CASCADE,

    UNIQUE KEY uk_obs_event
        (observation_id, event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- =====================================================
-- 7. 날씨 뉴스 테이블
-- =====================================================

SET @sql = CONCAT(
'CREATE TABLE IF NOT EXISTS weather_news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    region_id ', @region_id_type, ' NOT NULL,

    temp DECIMAL(5,2),
    weather_status VARCHAR(50) NOT NULL,
    warning_type VARCHAR(100) DEFAULT ''없음'',
    news_title VARCHAR(255) NOT NULL,
    news_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_news_region
        FOREIGN KEY (region_id)
        REFERENCES region(region_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- =====================================================
-- 8. 테이블 생성 확인
-- =====================================================

SHOW TABLES;

-- 실제 컬럼 자료형 확인
SELECT
    TABLE_NAME,
    COLUMN_NAME,
    COLUMN_TYPE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'weather_korea'
  AND COLUMN_NAME IN ('region_id', 'observation_id')
ORDER BY TABLE_NAME, COLUMN_NAME;


-- =====================================================
-- 9. 전국 지역 데이터 확인
-- =====================================================

SELECT *
FROM region
ORDER BY region_id;


-- =====================================================
-- 10. 최신 날씨 관측 조회
-- =====================================================

SELECT
    o.observation_id,
    r.region_name,
    o.temperature,
    o.humidity,
    o.wind_speed,
    o.precipitation,
    o.weather_code,
    o.observed_at
FROM weather_observation o
JOIN region r
    ON o.region_id = r.region_id
ORDER BY o.observed_at DESC
LIMIT 50;


-- =====================================================
-- 11. 기상 이벤트 조회
-- FastAPI get_latest_events()와 동일
-- =====================================================

SELECT
    e.event_id,
    e.region_id,
    r.region_name,
    e.event_type,
    e.severity_level,
    e.description,
    e.created_at
FROM weather_event e
JOIN region r
    ON e.region_id = r.region_id
ORDER BY e.created_at DESC
LIMIT 50;


-- =====================================================
-- 12. 날씨 뉴스 조회
-- =====================================================

SELECT
    n.id,
    r.region_name,
    n.temp,
    n.weather_status,
    n.warning_type,
    n.news_title,
    n.news_content,
    n.created_at
FROM weather_news n
JOIN region r
    ON n.region_id = r.region_id
ORDER BY n.created_at DESC
LIMIT 50;


-- =====================================================
-- 13. DB 연결 정보
-- =====================================================

SELECT
    DATABASE() AS database_name,
    @@hostname AS mysql_hostname,
    @@port AS mysql_port,
    @@server_uuid AS mysql_server_uuid;
