# /db-check — Supabase 연결 및 데이터 상태 확인

```bash
cd /workspaces/Edgar && python -c "
import os, sys
sys.path.insert(0, '.')
from shared.config import CONFIG

url = CONFIG.get('supabase_url')
key = CONFIG.get('supabase_key')

if not url or not key:
    print('❌ SUPABASE_URL 또는 SUPABASE_KEY 가 .env 에 없음')
    sys.exit(1)

from database.client import SupabaseDB
db = SupabaseDB(url, key)

tables = ['reports', 'market_data', 'youtube_videos', 'news_articles']
for t in tables:
    r = db.client.table(t).select('id', count='exact').execute()
    count = r.count if hasattr(r, 'count') else len(r.data)
    print(f'  {t}: {count}건')

last = db.latest_report()
if last:
    print(f\"\n최근 리포트: #{last['id']} ({last['created_at'][:16]})\")
    print(last.get('analysis','')[:300])
" 2>&1
```

결과를 바탕으로 DB 상태를 요약하고, 문제가 있으면 해결 방법을 제안하세요.
