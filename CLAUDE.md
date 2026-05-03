# Edgar — Claude Code 가이드

## 프로젝트 개요

시장 데이터(yfinance/CoinGecko), YouTube, RSS 뉴스를 수집·분석해  
텔레그램으로 전송하는 자동화 봇. Supabase(PostgreSQL)에 모든 데이터 보관.

**인프라**: GitHub Codespaces(개발) → Oracle Cloud ARM VM(운영)  
**AI**: Claude Sonnet(챗봇) + DeepSeek/Groq/Gemini(시장 분석)  
**영상**: Wan2.1 14B (fal.ai) AI 동영상 생성 → YouTube Shorts 자동 업로드

---

## 모듈 구조

```
shared/config.py          ← 전역 CONFIG (모든 모듈이 여기서 설정 읽음)
database/client.py        ← SupabaseDB (4개 테이블: market_data, youtube_videos, news_articles, reports)

telegram_bot/             ← 사용자 인터페이스
  main.py                 ← Application 생성 + 핸들러 등록 + 스케줄러 시작
  handlers/chat.py        ← Claude AI 자유 대화
  handlers/signal.py      ← /monitor (즉시 실행), /report (최근 리포트)
  handlers/settings.py    ← /style, /api, /status + InlineKeyboard 콜백
  services/claude_chat.py ← 사용자별 대화 기록 관리

kstock_signal/            ← 데이터 파이프라인
  scheduler.py            ← SignalScheduler (전체 파이프라인 오케스트레이터)
  main.py                 ← 단독 실행 진입점 (--once / --shorts / --korean / --dry 플래그)
  collectors/market.py    ← yfinance + CoinGecko (50+ 심볼)
  collectors/youtube.py   ← YouTube Data API + 자막
  collectors/news.py      ← RSS feedparser
  collectors/naver_report.py     ← 네이버 금융 종목분석 리포트 PDF 수집
  collectors/shortvideo_trend.py ← YouTube Trending(mostPopular) + 한/영 키워드 트렌드 수집
  analyzers/trend.py      ← TrendAnalyzer (deepseek/groq/gemini/claude)
  analyzers/script.py     ← ScriptGenerator (숏폼 스크립트 생성, 5포맷 + celeb_collab)
  analyzers/celeb_cast.py ← CelebCaster (리포트→CEO 캐릭터 매핑, 12개 기업 DB)
  generators/video.py     ← VideoGenerator (PIL+moviepy 정적 렌더러, 6포맷)
  generators/ai_video.py  ← AIVideoGenerator (Wan2.1 14B 병렬 AI 영상 생성, 폴백: 1.3B→Flux→PIL)
  generators/heygen.py    ← HeyGenClient (AI 아바타 영상 생성 API)
  reporters/telegram.py   ← TelegramReporter (메시지 포맷 + 발송)
```

## 데이터 흐름

```
SignalScheduler.run()
  │
  ├─ MarketCollector.collect()          → dict[symbol, price_data]
  ├─ YouTubeCollector.collect()         → list[video_dict]
  ├─ NewsCollector.collect()            → list[article_dict]
  │
  ├─ TrendAnalyzer.analyze()            → analysis: str
  │
  ├─ SupabaseDB.save_*()                → Supabase 저장
  ├─ /tmp/latest_report.txt             → /report 명령용 캐시
  ├─ TelegramReporter.send()            → 텔레그램 발송
  │
  └─ [SHORTVIDEO_ENABLED=true 시]
       ShortVideoTrendCollector.collect() → YouTube Trending + 키워드 트렌드 패턴
       NaverReportCollector.collect()     → PDF 리포트
       ScriptGenerator.generate_celeb()  → celeb_collab 스크립트 (LLM)
       AIVideoGenerator.generate()       → Wan2.1 14B 병렬 클립 → MP4
       YouTubePublisher.upload()         → YouTube Shorts 업로드
```

---

## 실행 방법

```bash
# 텔레그램 봇 (스케줄러 포함)
python telegram_bot/main.py

# 전체 파이프라인 1회 실행
python kstock_signal/main.py --once

# 전체 파이프라인 dry-run (텔레그램/업로드 생략)
python kstock_signal/main.py --once --dry

# 숏폼 영상 파이프라인만 실행 (Wan2.1 AI 영상 생성)
python kstock_signal/main.py --shorts --dry   # dry-run (영상 생성 O, 업로드 X)
python kstock_signal/main.py --shorts          # 실제 실행 (영상 생성 + YouTube 업로드)

# 한국어 30초 숏폼 파이프라인
python kstock_signal/main.py --korean --dry

# 헬스 체크
python scripts/health_check.py
```

---

## 환경변수 (.env)

| 변수 | 필수 | 설명 |
|------|------|------|
| 변수 | 필수 | 설명 |
|------|------|------|
| TELEGRAM_BOT_TOKEN    | ✅ | 텔레그램 봇 |
| ANTHROPIC_API_KEY     | ✅ | Claude AI 챗봇 |
| DEEPSEEK_API_KEY      | 권장 | 시장 분석 LLM |
| YOUTUBE_API_KEY       | 권장 | YouTube 수집 + 트렌드 수집 |
| FAL_KEY               | 권장 | fal.ai Wan2.1 AI 영상 생성 (https://fal.ai) |
| SHORTS_AI_BACKEND     | 선택 | **wan2**(권장) \| pollinations(무료) \| hf \| flux \| pil |
| SHORTVIDEO_ENABLED    | 선택 | true 시 숏폼 파이프라인 활성화 (기본 false) |
| HF_TOKEN              | 선택 | HuggingFace 토큰 (hf 백엔드 사용 시) |
| SUPABASE_URL          | 선택 | DB 저장 |
| SUPABASE_KEY          | 선택 | DB 저장 |
| LLM_PROVIDER          | 선택 | deepseek/groq/gemini/claude |
| REPORT_STYLE          | 선택 | aggressive/professional/... |
| REPORT_TIME           | 선택 | HH:MM (기본 08:00) |
| HEYGEN_API_KEY        | 선택 | HeyGen AI 아바타 영상 생성 |
| KOREAN_SHORTS_ENABLED | 선택 | true 시 한국어 30초 숏폼 파이프라인 활성화 |

---

## 코딩 컨벤션

- Python 3.12, async/await 사용
- 모든 파일 상단 `from __future__ import annotations`
- 타입 힌트 권장 (dict, list, str | None)
- config 접근은 항상 `.get()` 사용 (KeyError 방지)
- 외부 API 호출은 try/except 로 감싸고 None 반환

## 새 Collector 추가 방법

1. `kstock_signal/collectors/my_source.py` 생성
2. `async def collect(self) -> list[dict]` 메서드 구현
3. `kstock_signal/scheduler.py` `_init_components()` 에 추가
4. `database/schema.sql` 에 테이블 추가 (필요시)

## 새 텔레그램 명령어 추가 방법

1. `telegram_bot/handlers/` 에 핸들러 함수 작성
2. `telegram_bot/main.py` `create_app()` 에 `CommandHandler` 등록

---

## Self-Eval 체크리스트

코드 변경 후 반드시 확인:

```bash
# 1. lint
python -m ruff check . --fix

# 2. import 테스트
python -c "
from shared.config import CONFIG
from database.client import SupabaseDB
from kstock_signal.scheduler import SignalScheduler
from telegram_bot.main import create_app
print('✅ 모든 import OK')
"

# 3. 헬스 체크
python scripts/health_check.py
```

**코드 품질 기준:**
- 각 모듈은 단일 책임 (수집 / 분석 / 발송 분리)
- 외부 의존(API, DB) 실패 시 봇이 멈추지 않아야 함
- CONFIG 는 `shared/config.py` 에서만 정의

---

## Oracle Cloud 배포

```bash
# 배포
bash scripts/deploy_oracle.sh

# 원격 서비스 상태
ssh oracle-vm "systemctl status edgar-bot edgar-signal"
```

서비스 파일: `/etc/systemd/system/edgar-bot.service`  
로그: `journalctl -u edgar-bot -f`
