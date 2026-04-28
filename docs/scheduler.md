# 스케줄러·봇 운영 가이드

## 실행

```bash
python bot.py
```

## 스케줄

`config.py`의 `schedule` 설정으로 변경:

```python
'schedule': {
    'daily_report_time': '08:00',   # KST 기준
    'enabled': True
}
```

## 수동 실행 (텔레그램 명령어)

봇에 메시지를 보내 즉시 리포트 실행 가능 (bot.py 구현에 따라 다름)

## 수집 범위 설정

`config.py`에서 조정:

```python
'collection_timeframes': {
    'youtube': 24,   # 최근 N시간 영상 수집
    'website': 12,   # 최근 N시간 뉴스 수집
}
```

## 실행 흐름 (매일 08:00 KST)

```
1. YouTube 수집      → 카테고리별 최신 영상 + 자막
2. RSS/뉴스 수집     → 설정된 피드 전체
3. 시장 데이터 수집  → yfinance + CoinGecko
4. AI 분석           → LLM으로 트렌드·액션플랜 생성
5. Supabase 저장     → 전체 데이터 DB 적재
6. 파일 저장         → /tmp/latest_report.txt
7. 텔레그램 발송     → report_recipients 목록에 전송
```

## 리포트 수신자 변경

`config.py`의 `report_recipients`에 텔레그램 chat_id 추가/제거:

```python
'report_recipients': [개인_chat_id, 그룹_chat_id]
```

chat_id 확인: 텔레그램에서 `@userinfobot` 에게 메시지 전송
