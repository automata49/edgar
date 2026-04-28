# 코드 구조

## 디렉토리

```
Edgar/
├── bot.py                    # 텔레그램 봇 진입점
├── scheduler.py              # 주기적 작업 스케줄러
├── config.py                 # 전역 설정 (API 키, 채널 목록 등)
│
├── collectors/               # 데이터 수집
│   ├── market_data_collector.py      # yfinance + CoinGecko
│   ├── youtube_channel_collector.py  # YouTube Data API
│   ├── youtube_transcript_extractor.py
│   ├── website_collector.py          # RSS 피드
│   └── finviz_collector.py
│
├── analyzers/
│   └── trend_analyzer.py     # LLM 기반 트렌드 분석
│
├── reporters/
│   └── report_generator.py   # 텔레그램 메시지 포맷·발송
│
└── database/
    ├── supabase_client.py    # Supabase 저장 클라이언트
    └── schema.sql            # 테이블 생성 SQL
```

## 데이터 흐름

```
scheduler.py
  │
  ├─ collectors/ ──→ youtube_data, website_data, market_data
  │
  ├─ analyzers/  ──→ AI 분석 텍스트 (analysis)
  │
  ├─ database/   ──→ Supabase 저장
  │                  market_data / youtube_videos / news_articles / reports
  │
  └─ reporters/  ──→ 텔레그램 발송
```

## Supabase 테이블

| 테이블 | 저장 데이터 |
|--------|------------|
| `market_data` | 심볼별 가격·등락률 스냅샷 |
| `youtube_videos` | 영상 제목·URL·카테고리·자막 |
| `news_articles` | 뉴스 제목·URL·출처·요약 |
| `reports` | AI 분석 본문·액션플랜·시장 스냅샷 |
