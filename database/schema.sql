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

-- =============================================
-- 숏폼 콘텐츠 파이프라인
-- =============================================

-- 네이버 증권 리서치 리포트
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
CREATE INDEX IF NOT EXISTS idx_research_stock    ON research_reports (stock_name);
CREATE INDEX IF NOT EXISTS idx_research_collected ON research_reports (collected_at DESC);

-- 숏폼 트렌드 패턴 (AXON-style engagement DB)
CREATE TABLE IF NOT EXISTS shortform_trends (
    id               bigserial PRIMARY KEY,
    hook_type        text        NOT NULL,   -- question/shock_stat/bold_claim/listicle
    hook_text        text        NOT NULL,
    title_format     text,
    engagement_score bigint      DEFAULT 0,
    view_count       bigint      DEFAULT 0,
    like_count       bigint      DEFAULT 0,
    comment_count    bigint      DEFAULT 0,
    video_id         text        UNIQUE,
    channel_title    text,
    category         text        DEFAULT 'finance',
    published_at     timestamptz,
    collected_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_trends_hook_type   ON shortform_trends (hook_type);
CREATE INDEX IF NOT EXISTS idx_trends_engagement  ON shortform_trends (engagement_score DESC);
CREATE INDEX IF NOT EXISTS idx_trends_collected   ON shortform_trends (collected_at DESC);

-- 생성된 숏폼 스크립트
CREATE TABLE IF NOT EXISTS video_scripts (
    id             bigserial PRIMARY KEY,
    stock_name     text        NOT NULL,
    hook_type      text,
    hook_text      text,
    hook_subtext   text,
    first_frame    jsonb,
    intro_text     text,
    body_segments  jsonb,
    subtitles      jsonb,
    cta_text       text,
    hashtags       jsonb,
    title          text,
    description    text,
    report_id      text,
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_scripts_stock     ON video_scripts (stock_name);
CREATE INDEX IF NOT EXISTS idx_scripts_created   ON video_scripts (created_at DESC);

-- 업로드된 숏폼 영상
CREATE TABLE IF NOT EXISTS published_videos (
    id             bigserial PRIMARY KEY,
    script_id      bigint      REFERENCES video_scripts (id),
    platform       text        NOT NULL,   -- youtube / tiktok / instagram
    video_url      text,
    video_id       text,
    file_path      text,
    status         text        DEFAULT 'uploaded',  -- uploaded / failed / pending
    published_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_published_platform ON published_videos (platform);
CREATE INDEX IF NOT EXISTS idx_published_at        ON published_videos (published_at DESC);
