# Edgar — Claude Code 가이드

## 프로젝트 개요

시장 데이터(yfinance/CoinGecko), YouTube, RSS 뉴스를 수집·분석해  
텔레그램으로 전송하는 자동화 봇. Supabase(PostgreSQL)에 모든 데이터 보관.

**인프라**: GitHub Codespaces(개발) → Oracle Cloud ARM VM(운영)  
**AI**: 멀티 모델 — Gemini 무료 티어(분류·요약·일반 대화·시장 분석, 기본 gemini-3.8-flash) + GPT-6 Astra(종목 분석, 월 $20 상한) · `config/models.yaml` · DeepSeek 사용 안 함  
**투자 분석**: 계산은 Pepper(automata49/pepper)가 하고 Edgar는 results JSON을 읽어 전달·해석만 함  
**영상**: Wan2.1 14B (fal.ai) AI 동영상 생성 → YouTube Shorts 자동 업로드

---

## 모듈 구조

```
shared/config.py          ← 전역 CONFIG (모든 모듈이 여기서 설정 읽음)
database/client.py        ← SupabaseDB (4개 테이블: market_data, youtube_videos, news_articles, reports)

telegram_bot/             ← 사용자 인터페이스
  main.py                 ← Application 생성 + 핸들러 등록 + 스케줄러 시작
  handlers/chat.py        ← 자유 대화 (router_chat 사용)
  handlers/signal.py      ← /monitor (즉시 실행), /report (최근 리포트)
  handlers/settings.py    ← /style, /api, /status + InlineKeyboard 콜백
  handlers/pepper.py      ← /pepper, /stock, /budget, /rules
  handlers/browse.py      ← /view 버튼 메뉴 (Google 시트 + 수집 데이터 조회, "포트폴리오 보여줘" 같은 채팅도 연결)
  services/router_chat.py ← 멀티 모델 챗봇 (간단→Gemini, 분석→Astra)

llm/                      ← 멀티 모델 계층
  router.py               ← task → tier → 모델 선택, 예산 초과/오류 시 무료 모델로 대체
  budget.py               ← Astra 사용액 장부(data/llm_usage.csv) + 월 상한 가드
  providers/__init__.py   ← GeminiProvider, OpenAIProvider(Responses API)
  gemini_text.py          ← 파이프라인 분석기용 Gemini 호출 (3.8 Flash → 3.6 Flash 대체)
config/models.yaml        ← 모델·가격·작업별 티어·월 예산

invest/                   ← Pepper 연동
  pepper_results.py       ← results JSON 읽기·요약 (숫자 재계산 금지)
  prompts.py              ← 분석·대화·분류·정성 초안 프롬프트
  sheets.py               ← Pepper Google 시트 읽기 (읽기 전용, 5분 캐시, 실패 시 pepper sync 스냅샷)
  views.py                ← 텔레그램 화면 포맷터 (HTML 카드 + 인라인 버튼, 순수 함수)

kstock_signal/            ← 데이터 파이프라인
  scheduler.py            ← SignalScheduler (전체 파이프라인 오케스트레이터)
  main.py                 ← 단독 실행 진입점 (--once / --shorts / --korean / --dry 플래그)
  collectors/market.py    ← yfinance + CoinGecko (50+ 심볼)
  collectors/youtube.py   ← YouTube Data API + 자막
  collectors/news.py      ← RSS feedparser
  collectors/naver_report.py     ← 네이버 금융 종목분석 리포트 PDF 수집
  collectors/shortvideo_trend.py ← YouTube Trending(mostPopular) + 한/영 키워드 트렌드 수집
  analyzers/trend.py      ← TrendAnalyzer (gemini/groq/claude, 기본 gemini-3.8-flash)
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
| GEMINI_API_KEY        | ✅ | 무료 모델(분류·요약·대화) |
| OPENAI_API_KEY        | ✅ | GPT-6 Astra 분석 (월 $20 상한, config/models.yaml) |
| PEPPER_RESULTS        | 선택 | Pepper results JSON 경로 (기본 ../pepper/data/results/latest.json) |
| PEPPER_SHEET_ID       | 선택 | Pepper Google 시트 ID (기본 ../pepper/config/workspace.json) |
| GOOGLE_APPLICATION_CREDENTIALS | 선택 | 시트 직접 읽기용 서비스 계정 JSON (시트를 그 계정 이메일에 보기 권한 공유) |
| PEPPER_HISTORY        | 선택 | 시트 대체 스냅샷 폴더 (기본 ../pepper/data/history, `pepper sync`가 생성) |
| PEPPER_SHEET_SNAPSHOT | 선택 | 대체 스냅샷 JSON 파일 1개 |
| TELEGRAM_ALLOWED_IDS  | 선택 | /view 사용 가능한 텔레그램 user ID (쉼표 구분, 기본 report_recipients의 개인 ID) |
| EDGAR_MODELS_CONFIG   | 선택 | 모델 설정 파일 경로 (기본 config/models.yaml) |
| ANTHROPIC_API_KEY     | 선택 | 기존 Claude 챗봇 (현재 봇은 router_chat 사용) |
| YOUTUBE_API_KEY       | 권장 | YouTube 수집 + 트렌드 수집 |
| FAL_KEY               | 권장 | fal.ai Wan2.1 AI 영상 생성 (https://fal.ai) |
| SHORTS_AI_BACKEND     | 선택 | **wan2**(권장) \| pollinations(무료) \| hf \| flux \| pil |
| SHORTVIDEO_ENABLED    | 선택 | true 시 숏폼 파이프라인 활성화 (기본 false) |
| HF_TOKEN              | 선택 | HuggingFace 토큰 (hf 백엔드 사용 시) |
| SUPABASE_URL          | 선택 | DB 저장 |
| SUPABASE_KEY          | 선택 | DB 저장 |
| LLM_PROVIDER          | 선택 | gemini(기본)/groq/claude — 시장 분석·대본·리포트 요약용 |
| GEMINI_MODEL          | 선택 | 파이프라인 Gemini 모델 (기본 gemini-3.8-flash, 실패 시 gemini-3.6-flash) |
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

# 4. 멀티 모델 라우터 테스트 (네트워크 없이 가짜 모델로 검증)
python -m unittest discover -s tests -v
```

**모델 예산 규칙:**
- 유료 모델은 반드시 `ModelRouter.run(task, ...)`로만 호출 (직접 SDK 호출 금지 — 예산 가드 우회됨)
- 보유·계좌 정보가 들어가는 작업은 models.yaml에서 `private: true` (무료 Gemini로 보내지 않음)

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
