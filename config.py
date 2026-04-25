import os
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    # ==================== API 키 ====================
    'deepseek_api_key': os.getenv('DEEPSEEK_API_KEY'),
    'groq_api_key': os.getenv('GROQ_API_KEY'),
    'gemini_api_key': os.getenv('GEMINI_API_KEY'),
    'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY'),
    'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
    'youtube_api_key': os.getenv('YOUTUBE_API_KEY'),
    
    # ==================== LLM 설정 ====================
    'llm_provider': 'deepseek',
    'report_style': 'aggressive',
    
    # ==================== YouTube 채널 ====================
    'youtube_channels': {
        'market': [
            'https://www.youtube.com/@hkglobalmarket',
        ],
        'investment': [
            'https://www.youtube.com/@hs_academy',
            'https://www.youtube.com/@3protv',
            'https://www.youtube.com/@orlandocampus',
        ],
        'realestate': [
          # 'https://www.youtube.com/@chaeboosim',
	  # 'https://www.youtube.com/@kbland',
        ],
        'crypto': [
            'https://www.youtube.com/playlist?list=PLjVsiYZr4pXHt1tkOxoaMlfiE3NmX-KLy',
            'https://www.youtube.com/playlist?list=PLQvqXcm97CTDaa3h59Sbhj27iac6sLCRz',
        ]
    },
   
    # ==================== 웹사이트/RSS ====================
    'rss_feeds': [
        # 해커뉴스
        'https://news.ycombinator.com/rss',
        
        # 한국경제
        'https://www.hankyung.com/feed/all-news',
        'https://www.hankyung.com/feed/economy',
        'https://www.hankyung.com/feed/finance'
        'https://www.hankyung.com/feed/realestate',
        
        # 해외뉴스
        'https://finance.yahoo.com/rss/headline?s=AAPL,MSFT,GOOGL,TSLA,META,NVDA,005930.KS,ETH,BTC',
        'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114',
        'https://finance.yahoo.com/quote/RSS.L/new',
        'https://feeds.finance.yahoo.com/rss/2.0/headline?s=yhoo,goog&region=US&lang=en-US',
        'https://www.investing.com/rss/news.rss',
        
	# 연합뉴스 경제
        'https://www.yna.co.kr/rss/economy.xml',
        
        # 글로벌 암호화폐
        'https://cointelegraph.com/rss',
        'https://www.coindesk.com/arc/outboundfeeds/rss/',
    ],

    # ==================== 수집 설정 ====================
    'collection_timeframes': {
        'youtube': 24,
        'website': 12,
    },
    
    # ==================== 리포트 설정 ====================
    'report_recipients': [7491187317, -5249855498],
    
    # ==================== 스케줄 ====================
    'schedule': {
        'daily_report_time': '08:00',
        'enabled': True
    },
}
