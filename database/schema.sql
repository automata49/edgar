-- =============================================
-- Edgar 프로젝트 Supabase 스키마
-- Supabase SQL Editor에서 실행하세요
-- =============================================

-- 시장 데이터
CREATE TABLE IF NOT EXISTS market_data (
    id          bigserial PRIMARY KEY,
    symbol      text        NOT NULL,
    category    text        NOT NULL,
    price       numeric,
    change      numeric,
    change_pct  numeric,
    prev_close  numeric,
    collected_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data (symbol);
CREATE INDEX IF NOT EXISTS idx_market_data_collected_at ON market_data (collected_at DESC);

-- YouTube 영상
CREATE TABLE IF NOT EXISTS youtube_videos (
    id           bigserial PRIMARY KEY,
    video_id     text        UNIQUE,
    title        text        NOT NULL,
    url          text        NOT NULL,
    channel      text,
    category     text,
    transcript   text,
    published_at timestamptz,
    collected_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_youtube_category ON youtube_videos (category);
CREATE INDEX IF NOT EXISTS idx_youtube_collected_at ON youtube_videos (collected_at DESC);

-- 뉴스/RSS 기사
CREATE TABLE IF NOT EXISTS news_articles (
    id           bigserial PRIMARY KEY,
    title        text        NOT NULL,
    url          text        UNIQUE NOT NULL,
    source       text,
    summary      text,
    published_at timestamptz,
    collected_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_news_source ON news_articles (source);
CREATE INDEX IF NOT EXISTS idx_news_collected_at ON news_articles (collected_at DESC);

-- AI 분석 리포트
CREATE TABLE IF NOT EXISTS reports (
    id              bigserial PRIMARY KEY,
    analysis        text,
    action_plan     text,
    youtube_count   int,
    website_count   int,
    market_snapshot jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports (created_at DESC);
-- daily(매일 아침) / weekly(주간). 기존 행은 daily
ALTER TABLE reports ADD COLUMN IF NOT EXISTS kind text NOT NULL DEFAULT 'daily';
CREATE INDEX IF NOT EXISTS idx_reports_kind ON reports (kind, created_at DESC);

-- =============================================
-- 네이버 증권 종목분석 리포트 (리포트 1건 = 1행)
-- =============================================
CREATE TABLE IF NOT EXISTS research_reports (
    id           bigserial PRIMARY KEY,
    stock_name   text        NOT NULL,
    firm         text,
    title        text        NOT NULL,
    target_price text,
    report_date  text,
    pdf_url      text,
    report_id    text        UNIQUE,
    text_content text,
    key_numbers  jsonb,
    collected_at timestamptz NOT NULL DEFAULT now()
);
-- 요약·종목별 조회용 컬럼 (이미 만든 테이블에도 추가됨)
ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS stock_code     text;
ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS report_day     date;
ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS opinion        text;
ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS target_value   bigint;   -- 목표주가(원)
ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS target_change  text;     -- 상향/하향/유지/신규/미확인
ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS sentiment      text;     -- 긍정/중립/부정
ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS summary        jsonb;    -- one_line, key_points, risks, numbers ...
ALTER TABLE research_reports ADD COLUMN IF NOT EXISTS summary_model  text;
CREATE INDEX IF NOT EXISTS idx_research_stock      ON research_reports (stock_name);
CREATE INDEX IF NOT EXISTS idx_research_code       ON research_reports (stock_code);
CREATE INDEX IF NOT EXISTS idx_research_day        ON research_reports (report_day DESC);
CREATE INDEX IF NOT EXISTS idx_research_collected  ON research_reports (collected_at DESC);

-- 종목별 리서치 현황 (최신 리포트 + 건수). /view 리서치 목록·주간 리포트에서 사용
CREATE OR REPLACE VIEW stock_research AS
SELECT l.stock_name,
       l.stock_code,
       c.report_count,
       c.firm_count,
       c.reports_30d,
       l.report_day              AS last_report_day,
       l.firm                    AS last_firm,
       l.opinion                 AS last_opinion,
       l.target_value            AS last_target,
       l.target_change           AS last_target_change,
       l.sentiment               AS last_sentiment,
       l.summary ->> 'one_line'  AS last_one_line
FROM (
    SELECT DISTINCT ON (stock_name) *
    FROM research_reports
    ORDER BY stock_name, report_day DESC NULLS LAST, id DESC
) l
JOIN (
    SELECT stock_name,
           count(*)                                                AS report_count,
           count(DISTINCT firm)                                    AS firm_count,
           count(*) FILTER (WHERE report_day >= current_date - 30) AS reports_30d
    FROM research_reports
    GROUP BY stock_name
) c USING (stock_name);
