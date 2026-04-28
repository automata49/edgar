import os
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 (shared/config.py 기준 한 단계 위)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CONFIG: dict = {
    # ── API Keys ─────────────────────────────────────────────
    "deepseek_api_key":  os.getenv("DEEPSEEK_API_KEY"),
    "groq_api_key":      os.getenv("GROQ_API_KEY"),
    "gemini_api_key":    os.getenv("GEMINI_API_KEY"),
    "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
    "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
    "youtube_api_key":   os.getenv("YOUTUBE_API_KEY"),

    # ── Supabase ─────────────────────────────────────────────
    "supabase_url": os.getenv("SUPABASE_URL"),
    "supabase_key": os.getenv("SUPABASE_KEY"),

    # ── LLM ──────────────────────────────────────────────────
    "llm_provider":  os.getenv("LLM_PROVIDER", "deepseek"),
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
        "daily_report_time": os.getenv("REPORT_TIME", "08:00"),
        "enabled": True,
    },

    # ── Naver Research Report ─────────────────────────────────
    "naver_report": {
        "target_symbols": [],
        "max_reports": 3,
    },

    # ── Short-form Video Pipeline ─────────────────────────────
    "shortvideo": {
        "enabled":           os.getenv("SHORTVIDEO_ENABLED", "false").lower() == "true",
        "trend_max_results": 10,
        "output_dir":        os.getenv("SHORTS_OUTPUT_DIR", os.path.join(_PROJECT_ROOT, "output", "shorts")),
        # AI 영상 백엔드
        #   pollinations — Pollinations.ai Flux.1  키 불필요·완전 무료  ← 기본값
        #   horde        — StableHorde SDXL  커뮤니티GPU·완전 무료오픈소스
        #   hf           — HuggingFace FLUX.1-schnell  무료(HF_TOKEN 권장)
        #   flux         — fal.ai Flux  고품질         (FAL_KEY 필요)
        #   wan2         — fal.ai Wan2.1 실제 AI 영상  (FAL_KEY 필요)
        #   pil          — 향상된 PIL 로컬 렌더러
        "ai_backend":        os.getenv("SHORTS_AI_BACKEND", "pollinations"),
    },

    # ── fal.ai (Flux / Wan2.1 오픈소스 모델) ──────────────────
    "fal_api_key":  os.getenv("FAL_KEY", ""),

    # ── YouTube Shorts Upload ─────────────────────────────────
    "youtube_shorts": {
        "client_secrets_file": os.getenv("YOUTUBE_CLIENT_SECRETS", ""),
        "credentials_file":    os.getenv("YOUTUBE_CREDENTIALS_FILE", "/tmp/yt_credentials.json"),
        "category_id":         "22",
        "privacy_status":      os.getenv("YOUTUBE_PRIVACY", "public"),
    },
}
