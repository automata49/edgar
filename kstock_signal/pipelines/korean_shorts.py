from __future__ import annotations

"""
KoreanShortsPipeline — 네이버 리포트 → 30초 한국어 숏폼 영상 완성 파이프라인.

흐름:
  1. NaverReportCollector   → PDF 다운로드 + data/naver_reports/{종목}/ 저장
  2. ReportSummarizer       → 종목별 한국어 요약 + data/summaries/{종목}_summary.json
  3. KoreanShortScriptGenerator → 30초 대본 + data/scripts/{종목}_script.json
  4. AIVideoGenerator       → AI 배경 + TTS + Ken Burns + data/videos/{종목}_shorts.mp4
  5. TelegramReporter       → 영상 파일 텔레그램 전송 (선택)
"""

import os
from pathlib import Path


class KoreanShortsPipeline:
    """
    1단계(요약) + 2단계(대본) + 영상 생성까지 원스톱 실행.

    Usage:
        pipeline = KoreanShortsPipeline(CONFIG, bot=telegram_bot)
        result   = await pipeline.run()          # 전체 실행
        result   = await pipeline.run(dry_run=True)  # 영상 생성만, 텔레그램 생략
    """

    def __init__(self, config: dict, bot=None) -> None:
        self.config = config
        self.bot    = bot
        self._init_components()

    # ── Init ─────────────────────────────────────────────────────────────────

    def _init_components(self) -> None:
        from kstock_signal.collectors.naver_report         import NaverReportCollector
        from kstock_signal.analyzers.report_summarizer     import ReportSummarizer
        from kstock_signal.analyzers.korean_script         import KoreanShortScriptGenerator
        from kstock_signal.generators.ai_video             import AIVideoGenerator

        # max_reports는 korean_shorts 설정에서 오버라이드 가능
        cfg_kr    = self.config.get("korean_shorts", {})
        max_r     = cfg_kr.get("max_reports", 5)
        cfg_naver = {**self.config, "naver_report": {**self.config.get("naver_report", {}), "max_reports": max_r}}

        self.collector  = NaverReportCollector(cfg_naver)
        self.summarizer = ReportSummarizer(self.config)
        self.script_gen = KoreanShortScriptGenerator(self.config)

        # AIVideoGenerator는 shortvideo.output_dir 대신 korean_script.video_dir 사용
        video_dir = self.config.get("korean_script", {}).get(
            "video_dir",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "videos"),
        )
        Path(video_dir).mkdir(parents=True, exist_ok=True)
        ai_cfg  = {**self.config, "shortvideo": {**self.config.get("shortvideo", {}), "output_dir": video_dir}}
        self.video_gen  = AIVideoGenerator(ai_cfg)

        self.notify     = cfg_kr.get("notify_telegram", True)

    # ── Public ───────────────────────────────────────────────────────────────

    async def run(self, dry_run: bool = False) -> dict:
        """
        전체 파이프라인 실행.

        Returns:
            {
              "reports":   int,   # 수집된 리포트 수
              "summaries": int,   # 생성된 요약 수
              "scripts":   int,   # 생성된 대본 수
              "videos":  list[str],  # 생성된 영상 경로
              "sent":    list[str],  # 텔레그램 전송된 종목
            }
        """
        print("\n" + "─" * 55)
        print("🇰🇷 Korean Shorts Pipeline 시작")
        print("─" * 55)

        result = {"reports": 0, "summaries": 0, "scripts": 0, "videos": [], "sent": []}

        # ── 1단계: 리포트 수집 ────────────────────────────────────────────────
        print("\n[1/4] 📑 네이버 리포트 수집 + PDF 저장")
        reports = await self.collector.collect()
        result["reports"] = len(reports)
        if not reports:
            print("   ⚠️  수집된 리포트 없음 — 파이프라인 종료")
            return result
        print(f"   ✅ {len(reports)}건 수집 완료")

        # ── 2단계: 종목별 요약 ───────────────────────────────────────────────
        print("\n[2/4] 📝 종목별 한국어 요약 생성")
        summaries = self.summarizer.summarize_by_stock(reports)
        result["summaries"] = len(summaries)
        print(f"   ✅ {len(summaries)}개 종목 요약 완료")

        # ── 3단계: 30초 대본 생성 ────────────────────────────────────────────
        print("\n[3/4] 🎬 30초 한국어 대본 생성")
        scripts = self.script_gen.generate_batch(summaries)
        result["scripts"] = len(scripts)
        print(f"   ✅ {len(scripts)}개 대본 생성 완료")

        # ── 4단계: 영상 생성 + 전송 ─────────────────────────────────────────
        print("\n[4/4] 🎥 AI 영상 생성")
        for script in scripts:
            spec       = script.to_video_spec()
            video_path = self.video_gen.generate(spec)

            if video_path:
                result["videos"].append(video_path)
                print(f"   📹 {script.stock_name}: {video_path}")

                if not dry_run and self.notify and self.bot:
                    sent = await self._send_video(video_path, script)
                    if sent:
                        result["sent"].append(script.stock_name)
            else:
                print(f"   ⚠️  {script.stock_name}: 영상 생성 실패")

        print(
            f"\n✅ Korean Shorts 완료 — "
            f"리포트 {result['reports']}건 · "
            f"요약 {result['summaries']}개 · "
            f"대본 {result['scripts']}개 · "
            f"영상 {len(result['videos'])}개 · "
            f"전송 {len(result['sent'])}개"
        )
        print("─" * 55 + "\n")
        return result

    # ── Telegram 전송 ────────────────────────────────────────────────────────

    async def _send_video(self, video_path: str, script) -> bool:
        """영상 파일을 텔레그램 recipients 에게 전송."""
        recipients = self.config.get("report_recipients", [])
        if not recipients:
            return False

        caption = (
            f"📊 *{script.stock_name}* 30초 분석\n\n"
            f"▸ {script.hook}\n"
            f"▸ {' · '.join(script.key_themes[:2])}\n\n"
            f"#주식분석 #경제공부 #숏폼"
        )

        sent = False
        for chat_id in recipients:
            try:
                with open(video_path, "rb") as vf:
                    await self.bot.send_video(
                        chat_id=chat_id,
                        video=vf,
                        caption=caption,
                        parse_mode="Markdown",
                        supports_streaming=True,
                    )
                sent = True
                print(f"   📤 전송 완료: {chat_id}")
            except Exception as e:
                print(f"   ⚠️  전송 실패 ({chat_id}): {e}")

        return sent

    # ── Standalone entry point ────────────────────────────────────────────────

    @classmethod
    async def run_once(cls, config: dict, dry_run: bool = False) -> dict:
        """설정만으로 파이프라인 1회 실행 (봇 연결 없이)."""
        pipeline = cls(config, bot=None)
        return await pipeline.run(dry_run=dry_run)
