# /run-signal — kstock_signal 수동 실행 (dry-run)

텔레그램 발송 없이 수집·분석 파이프라인을 테스트합니다.

```bash
cd /workspaces/Edgar && python kstock_signal/main.py --once --dry 2>&1
```

실행 후 다음을 확인하고 보고하세요:
- 수집 성공/실패 항목 (YouTube, 뉴스, 시장 데이터)
- AI 분석 결과 요약 (처음 500자)
- DB 저장 결과 (Supabase 연결된 경우)
- 에러가 있다면 원인과 해결 방법
