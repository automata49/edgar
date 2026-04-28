# Supabase 연동 가이드

## 1. 프로젝트 생성

1. [supabase.com](https://supabase.com) → New Project
2. Project URL과 API Key 복사 (`anon` 키 또는 `service_role` 키)
3. `.env`에 입력:
   ```
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_KEY=eyJ...
   ```

## 2. 테이블 생성

Supabase 대시보드 → **SQL Editor** → `database/schema.sql` 전체 붙여넣기 → **Run**

생성되는 테이블:
- `market_data` — 시장 데이터 스냅샷
- `youtube_videos` — YouTube 영상 (video_id 중복 제거)
- `news_articles` — 뉴스/RSS (URL 중복 제거)
- `reports` — AI 분석 리포트

## 3. 데이터 조회 예시

**최근 리포트 조회:**
```sql
SELECT created_at, youtube_count, website_count, analysis
FROM reports
ORDER BY created_at DESC
LIMIT 5;
```

**특정 심볼 시계열:**
```sql
SELECT collected_at, price, change_pct
FROM market_data
WHERE symbol = 'BTC'
ORDER BY collected_at DESC
LIMIT 30;
```

**오늘 수집된 뉴스:**
```sql
SELECT title, source, url
FROM news_articles
WHERE collected_at > now() - interval '24 hours'
ORDER BY collected_at DESC;
```

## 4. 주의사항

- `service_role` 키는 RLS(Row Level Security)를 우회하므로 서버 전용으로만 사용
- `anon` 키 사용 시 Supabase 대시보드에서 테이블 RLS 정책 설정 필요
