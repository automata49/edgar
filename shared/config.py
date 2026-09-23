import os
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 (shared/config.py 기준 한 단계 위)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CONFIG: dict = {
    # ── API Keys ─────────────────────────────────────────────
    "groq_api_key":      os.getenv("GROQ_API_KEY"),
    "gemini_api_key":    os.getenv("GEMINI_API_KEY"),
    "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
    "openai_api_key":    os.getenv("OPENAI_API_KEY"),

    # ── Pepper 연동 · 멀티 모델 ──────────────────────────────
    "models_config":  os.getenv("EDGAR_MODELS_CONFIG", os.path.join(_PROJECT_ROOT, "config", "models.yaml")),
    "pepper_results": os.getenv("PEPPER_RESULTS", os.path.join(_PROJECT_ROOT, "..", "pepper", "data", "results", "latest.json")),
    # Pepper Google 시트 (읽기 전용). ID 미지정 시 ../pepper/config/workspace.json 사용
    "pepper_sheet_id":       os.getenv("PEPPER_SHEET_ID"),
    "pepper_workspace":      os.path.join(_PROJECT_ROOT, "..", "pepper", "config", "workspace.json"),
    "pepper_history":        os.getenv("PEPPER_HISTORY", os.path.join(_PROJECT_ROOT, "..", "pepper", "data", "history")),
    "pepper_sheet_snapshot": os.getenv("PEPPER_SHEET_SNAPSHOT"),
    # /view 로 개인 데이터를 볼 수 있는 텔레그램 user/chat ID (쉼표 구분). 미지정 시 report_recipients
    "telegram_allowed_ids":  [int(x) for x in os.getenv("TELEGRAM_ALLOWED_IDS", "").replace(" ", "").split(",")
                              if x.lstrip("-").isdigit()],

    "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
    "youtube_api_key":   os.getenv("YOUTUBE_API_KEY"),

    # ── Supabase ─────────────────────────────────────────────
    "supabase_url": os.getenv("SUPABASE_URL"),
    "supabase_key": os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY"),

    # ── LLM ──────────────────────────────────────────────────
    # 시장 분석·숏폼 대본·리포트 요약 LLM: gemini(기본) | groq | claude. DeepSeek은 사용하지 않음
    "llm_provider":  os.getenv("LLM_PROVIDER", "gemini").lower().replace("deepseek", "gemini"),
    "gemini_model":  os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    # 기본 모델이 과부하(503)·오류일 때 차례로 시도 (config/models.yaml free 티어와 같은 순서)
    "gemini_fallback_models": ["gemini-3.6-flash"],
    "report_style":  os.getenv("REPORT_STYLE", "aggressive"),

    # ── YouTube Channels ─────────────────────────────────────
    "youtube_channels": {
        "market": [
            "https://www.youtube.com/@hkglobalmarket",
        ],
        "investment": [
            "https://www.youtube.com/@hs_academy",
            "https://www.youtube.com/@3protv",
            "https://www.youtube.com/@orlandocampus",
        ],
        "realestate": [],
        "crypto": [
            "https://www.youtube.com/playlist?list=PLjVsiYZr4pXHt1tkOxoaMlfiE3NmX-KLy",
            "https://www.youtube.com/playlist?list=PLQvqXcm97CTDaa3h59Sbhj27iac6sLCRz",
        ],
    },

    # ── RSS Feeds ────────────────────────────────────────────
    "rss_feeds": [
        "https://news.ycombinator.com/rss",
        "https://www.hankyung.com/feed/all-news",
        "https://www.hankyung.com/feed/economy",
        "https://www.hankyung.com/feed/finance",
        "https://www.hankyung.com/feed/realestate",
        "https://finance.yahoo.com/rss/headline?s=AAPL,MSFT,GOOGL,TSLA,META,NVDA",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "https://www.yna.co.kr/rss/economy.xml",
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
    ],

    # ── Collection ───────────────────────────────────────────
    "collection_timeframes": {
        "youtube": 24,
        "website": 12,
    },

    # ── Report ───────────────────────────────────────────────
    "report_recipients": [7491187317, -5249855498],

    # ── Schedule ─────────────────────────────────────────────
    "schedule": {
        "daily_report_time":  os.getenv("REPORT_TIME", "08:00"),
        # 주간 리포트: 요일(mon~sun) + 시각, KST
        "weekly_report_day":  os.getenv("WEEKLY_REPORT_DAY", "sat"),
        "weekly_report_time": os.getenv("WEEKLY_REPORT_TIME", "09:00"),
        "enabled": True,
    },

    # ── Naver Research Report (종목분석 리포트 → 요약 → 종목별 DB) ──
    "naver_report": {
        # 비우면 전체 종목. 예: NAVER_TARGETS="삼성전자,SK하이닉스,005930"
        "target_symbols": [x.strip() for x in os.getenv("NAVER_TARGETS", "").split(",") if x.strip()],
        "max_reports": int(os.getenv("NAVER_MAX_REPORTS", "20")),   # 1회 실행당 새로 요약할 최대 건수
        "pages":       int(os.getenv("NAVER_PAGES", "2")),          # 목록 페이지 수 (페이지당 약 30건)
        "max_text_chars": 6000,                                     # 요약에 넣을 PDF 본문 길이
        "save_dir": os.getenv("NAVER_REPORT_DIR", os.path.join(_PROJECT_ROOT, "data", "naver_reports")),
    },
}
