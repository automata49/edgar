# /eval — Edgar 코드 품질 자체 평가

다음 순서로 Edgar 프로젝트를 평가하고 결과를 보고하세요.

## 1. Lint 검사
```bash
cd /workspaces/Edgar && python -m ruff check . 2>&1
```

## 2. Import 테스트
```bash
cd /workspaces/Edgar && python -c "
from shared.config import CONFIG
from database.client import SupabaseDB
from kstock_signal.scheduler import SignalScheduler
from telegram_bot.main import create_app
print('✅ 모든 import OK')
" 2>&1
```

## 3. 헬스 체크
```bash
cd /workspaces/Edgar && python scripts/health_check.py 2>&1
```

## 4. 평가 항목
위 명령어 실행 후 다음을 분석하세요:
- lint 에러/경고 목록과 심각도
- import 실패 시 원인
- DB 연결 상태
- 개선 제안 상위 3가지 (중요도 순)

결과를 한국어로 간결하게 보고하세요.
