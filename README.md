# Edgar

시장 데이터·YouTube·뉴스를 수집·분석해 텔레그램으로 전송하는 자동화 봇.  
수집 데이터는 Supabase(PostgreSQL)에 저장됩니다.

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 3. Supabase 테이블 생성
# → Supabase SQL Editor에서 database/schema.sql 실행

# 4. 봇 실행
python bot.py
```

## 문서

| 문서 | 내용 |
|------|------|
| [docs/setup.md](docs/setup.md) | 환경변수·의존성 설정 |
| [docs/architecture.md](docs/architecture.md) | 코드 구조 및 데이터 흐름 |
| [docs/supabase.md](docs/supabase.md) | Supabase 연동 가이드 |
| [docs/scheduler.md](docs/scheduler.md) | 스케줄러·봇 운영 가이드 |
