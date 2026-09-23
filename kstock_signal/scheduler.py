from __future__ import annotations

import asyncio
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


class SignalScheduler:
    """kstock_signal 파이프라인 오케스트레이터 (Daily · Weekly · 리서치 리포트)."""

    def __init__(self, config: dict, bot=None, db=None, router=None) -> None:
        self.config = config
        self.bot    = bot
        self.db     = db
        self.router = router
        self._sched: AsyncIOScheduler | None = None
        self._init_components()

    # ── Public ───────────────────────────────────────────────────────────────

    def start(self) -> None:
        kst   = pytz.timezone("Asia/Seoul")
        sched = self.config.get("schedule", {})
        daily = sched.get("daily_report_time", "08:00")
        wday  = sched.get("weekly_report_day", "sat")
        wtime = sched.get("weekly_report_time", "09:00")

        self._sched = AsyncIOScheduler(timezone=kst)
        h, m = daily.split(":")
        self._sched.add_job(self.run, CronTrigger(hour=int(h), minute=int(m), timezone=kst), id="daily_signal")
        h, m = wtime.split(":")
        self._sched.add_job(self.run_weekly, CronTrigger(day_of_week=wday, hour=int(h), minute=int(m), timezone=kst),
                            id="weekly_report")
        self._sched.start()

        d_next = self._sched.get_job("daily_signal").next_run_time
        w_next = self._sched.get_job("weekly_report").next_run_time
        print(f"⏰ 스케줄러 시작 — Daily 매일 {daily} (다음: {d_next:%Y-%m-%d %H:%M}) · "
              f"Weekly {wday} {wtime} (다음: {w_next:%Y-%m-%d %H:%M}) KST\n")

    def stop(self) -> None:
        if self._sched and self._sched.running:
            self._sched.shutdown(wait=False)

    async def run(self, dry_run: bool = False) -> dict:
        """Daily 파이프라인. dry_run=True 이면 텔레그램 발송 생략."""
        print("\n" + "=" * 60)
        print("🚀 Daily 리포트 시작")
        print("=" * 60 + "\n")

        # 1. 수집
        youtube_data = await self.youtube.collect() if self.youtube else []
        news_data    = await self.news.collect()
        market_data  = self.market.collect()
        research     = await self.run_research()

        # 2. 분석
        print("🤖 AI 분석 중...")
        analysis = self.analyzer.analyze(youtube_data, news_data, market_data, research)
        print("✅ 분석 완료\n")

        stats = {"youtube_count": len(youtube_data), "website_count": len(news_data),
                 "research_count": len(research)}

        # 3. DB 저장
        if self.db:
            self._save_to_db(market_data, youtube_data, news_data, analysis, stats)

        # 4. /tmp 파일 저장 (챗봇 /report 용)
        self._save_tmp(analysis, stats, market_data)

        # 5. 텔레그램 발송
        if not dry_run and self.bot:
            await self._broadcast(analysis, stats, market_data, youtube_data, news_data, research)

        print("✅ 완료\n" + "=" * 60 + "\n")
        return {"analysis": analysis, "stats": stats, "research": research}

    async def run_research(self) -> list[dict]:
        """네이버 종목분석 리포트 수집 → 요약 → DB 저장. 실패해도 Daily는 계속."""
        try:
            return await self.research.run()
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠️  리서치 리포트 파이프라인 오류: {e}")
            return []

    async def run_weekly(self, dry_run: bool = False, chat_ids: list[int] | None = None) -> dict | None:
        """Weekly 리포트 생성·저장·발송. chat_ids 를 주면 그 대상에게만 보냅니다."""
        from kstock_signal.weekly import WeeklyReport

        print("🗓 Weekly 리포트 생성 중...")
        report = await asyncio.to_thread(WeeklyReport(self.config, self.router, self.db).build)
        if report is None:
            print("   ⚠️  Weekly 리포트는 Supabase 저장 데이터가 필요합니다")
            return None
        if self.db:
            try:
                self.db.save_report(report["text"], {}, None, kind="weekly")
            except Exception as e:  # noqa: BLE001
                print(f"   ⚠️  Weekly 저장 실패: {e}")
        if not dry_run and self.reporter:
            for chat_id in chat_ids or self.config.get("report_recipients", []):
                await self.reporter.send_text(chat_id, report["text"])
        print("✅ Weekly 완료\n")
        return report

    # ── Init ─────────────────────────────────────────────────────────────────

    def _init_components(self) -> None:
        from kstock_signal.analyzers.trend    import TrendAnalyzer
        from kstock_signal.collectors.market  import MarketCollector
        from kstock_signal.collectors.news    import NewsCollector
        from kstock_signal.reporters.telegram import TelegramReporter
        from kstock_signal.research           import ResearchPipeline

        if self.router is None:
            from llm.router import ModelRouter
            self.router = ModelRouter.from_config(self.config.get("models_config"))

        self.market   = MarketCollector(self.config)
        self.news     = NewsCollector(self.config)
        self.analyzer = TrendAnalyzer(self.config)
        self.research = ResearchPipeline(self.config, self.router, self.db)
        self.reporter = TelegramReporter(self.bot) if self.bot else None

        yt_key = self.config.get("youtube_api_key")
        if yt_key:
            from kstock_signal.collectors.youtube import YouTubeCollector
            self.youtube = YouTubeCollector(yt_key, self.config)
            print("✅ YouTube 수집기 활성")
        else:
            self.youtube = None
            print("⚠️  YouTube 수집기 비활성 (API 키 없음)")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _save_to_db(self, market_data, youtube_data, news_data, analysis, stats) -> None:
        try:
            from kstock_signal.collectors.market import CATEGORY_MAP
            n_m = self.db.save_market_data(market_data, CATEGORY_MAP)
            n_y = self.db.save_youtube_videos(youtube_data)
            n_n = self.db.save_news_articles(news_data)
            rid = self.db.save_report(analysis, stats, market_data)
            print(f"💾 DB: 시장 {n_m}건 · YouTube {n_y}건 · 뉴스 {n_n}건 · 리포트 #{rid}\n")
        except Exception as e:
            print(f"   ⚠️  DB 저장 실패: {e}\n")

    def _save_tmp(self, analysis: str, stats: dict, market_data: dict) -> None:
        try:
            lines = [
                f"수집 날짜: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"YouTube: {stats.get('youtube_count', 0)}개",
                f"뉴스: {stats.get('website_count', 0)}개",
                f"증권사 리포트: {stats.get('research_count', 0)}건",
                "",
            ]
            if market_data:
                lines.append("=== 시장 데이터 ===")
                for sym, d in market_data.items():
                    lines.append(f"{sym}: ${d.get('price',0):,.2f} ({d.get('change_percent',0):+.2f}%)")
                lines.append("")
            lines += ["=== AI 분석 ===", analysis]

            with open("/tmp/latest_report.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception as e:
            print(f"   ⚠️  파일 저장 실패: {e}")

    async def _broadcast(self, analysis, stats, market_data, youtube_data, news_data, research=None) -> None:
        recipients = self.config.get("report_recipients", [])
        print(f"📤 발송 ({len(recipients)}명)...")
        for chat_id in recipients:
            await self.reporter.send(chat_id, analysis, stats, market_data, youtube_data, news_data, research)
            print(f"   ✅ {chat_id}")
