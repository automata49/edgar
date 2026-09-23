"""kstock_signal 단독 실행 진입점 (텔레그램 봇 없이 파이프라인만 실행).

  python kstock_signal/main.py --once [--dry]      Daily 1회 (시장·뉴스·YouTube·리서치 → 분석 → 발송)
  python kstock_signal/main.py --weekly [--dry]    Weekly 1회 (지난 7일 저장 데이터 → 집계 + AI 해설)
  python kstock_signal/main.py --research          네이버 리서치 리포트만 수집·요약·저장
  python kstock_signal/main.py                     스케줄 모드 (Daily 매일 · Weekly 주 1회)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.client import SupabaseDB
from kstock_signal.reporters.research_text import daily_section
from kstock_signal.scheduler import SignalScheduler
from shared.config import CONFIG


def build_db() -> SupabaseDB | None:
    url = CONFIG.get("supabase_url")
    key = CONFIG.get("supabase_key")
    if url and key:
        return SupabaseDB(url, key)
    print("⚠️  Supabase 비활성 (환경변수 없음)")
    return None


async def main() -> None:
    db        = build_db()
    scheduler = SignalScheduler(CONFIG, bot=None, db=db)
    dry       = "--dry" in sys.argv

    if "--research" in sys.argv:
        rows = await scheduler.run_research()
        print(daily_section(rows) or "새 리포트가 없습니다.")

    elif "--weekly" in sys.argv:
        report = await scheduler.run_weekly(dry_run=dry)
        if report:
            print(report["text"])

    elif "--once" in sys.argv:
        await scheduler.run(dry_run=dry)

    else:
        scheduler.start()
        print("Ctrl+C 로 종료\n")
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            scheduler.stop()
            print("종료")


if __name__ == "__main__":
    asyncio.run(main())
