# 환경 설정

## 필수 환경변수 (.env)

```env
# LLM
DEEPSEEK_API_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
ANTHROPIC_API_KEY=

# 텔레그램
TELEGRAM_BOT_TOKEN=

# YouTube Data API v3
YOUTUBE_API_KEY=

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
```

## 의존성 설치

```bash
pip install -r requirements.txt
```

주요 패키지:
- `python-telegram-bot` — 텔레그램 봇
- `yfinance` — 주식/시장 데이터
- `feedparser` — RSS 수집
- `google-api-python-client` — YouTube API
- `youtube-transcript-api` — 자막 추출
- `supabase` — DB 연동
- `apscheduler` — 스케줄링
- `openai` — DeepSeek/Groq 호환 클라이언트

## LLM 선택

`config.py`의 `llm_provider` 값으로 변경:

| 값 | 모델 |
|----|------|
| `deepseek` | DeepSeek V3 (기본값) |
| `groq` | Groq (빠른 추론) |
| `gemini` | Google Gemini |
| `claude` | Anthropic Claude |
