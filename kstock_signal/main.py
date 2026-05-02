"""kstock_signal 단독 실행 진입점 (텔레그램 봇 없이 신호만 실행)."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared.config import CONFIG
from database.client import SupabaseDB
from kstock_signal.scheduler import SignalScheduler


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

    if "--korean" in sys.argv:
        # 한국어 30초 숏폼 파이프라인 단독 실행
        from kstock_signal.pipelines.korean_shorts import KoreanShortsPipeline
        pipeline = KoreanShortsPipeline(CONFIG, bot=None)
        result   = await pipeline.run(dry_run=dry)
        print(
            f"\n결과: 리포트 {result['reports']}건 · 요약 {result['summaries']}개 · "
            f"대본 {result['scripts']}개 · 영상 {len(result['videos'])}개"
        )

    elif "--shorts" in sys.argv:
        # 엔터테인먼트 숏폼 파이프라인만 실행
        result = await scheduler._run_shorts_pipeline(dry_run=dry)
        print(f"\n결과: 스크립트 {len(result['scripts'])}개 · 영상 {len(result['videos'])}개 · 업로드 {len(result['uploads'])}개")

    elif "--once" in sys.argv:
        # 전체 파이프라인 1회 실행
        await scheduler.run(dry_run=dry)

    else:
        # 스케줄 모드 (매일 08:00 KST)
        scheduler.start()
        print("Ctrl+C 로 종료\n")
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            scheduler.stop()
            print("종료")


if __name__ == "__main__":
    asyncio.run(main())
