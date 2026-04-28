from __future__ import annotations

from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


class SignalScheduler:
    """kstock_signal 전체 파이프라인 오케스트레이터."""

    def __init__(self, config: dict, bot=None, db=None) -> None:
        self.config = config
        self.bot    = bot
        self.db     = db
        self._sched: AsyncIOScheduler | None = None
        self._init_components()

    # ── Public ───────────────────────────────────────────────────────────────

    def start(self) -> None:
        kst  = pytz.timezone("Asia/Seoul")
        time = self.config.get("schedule", {}).get("daily_report_time", "08:00")
        h, m = time.split(":")

        self._sched = AsyncIOScheduler(timezone=kst)
        self._sched.add_job(
            self.run,
            CronTrigger(hour=int(h), minute=int(m), timezone=kst),
            id="daily_signal",
        )
        self._sched.start()

        next_run = self._sched.get_job("daily_signal").next_run_time
        print(f"⏰ 스케줄러 시작 — 매일 {time} KST (다음: {next_run.strftime('%Y-%m-%d %H:%M')})\n")

    def stop(self) -> None:
        if self._sched and self._sched.running:
            self._sched.shutdown(wait=False)

    async def run(self, dry_run: bool = False) -> dict:
        """전체 파이프라인 실행. dry_run=True 이면 텔레그램 발송 생략."""
        print("\n" + "=" * 60)
        print("🚀 kstock_signal 시작")
        print("=" * 60 + "\n")

        # 1. 수집
        youtube_data = await self.youtube.collect() if self.youtube else []
        news_data    = await self.news.collect()
        market_data  = self.market.collect()

        # 2. 분석
        print("🤖 AI 분석 중...")
        analysis = self.analyzer.analyze(youtube_data, news_data, market_data)
        print("✅ 분석 완료\n")

        stats = {"youtube_count": len(youtube_data), "website_count": len(news_data)}

        # 3. DB 저장
        if self.db:
            self._save_to_db(market_data, youtube_data, news_data, analysis, stats)

        # 4. /tmp 파일 저장 (챗봇 /report 용)
        self._save_tmp(analysis, stats, market_data)

        # 5. 텔레그램 발송
        if not dry_run and self.bot:
            await self._broadcast(analysis, stats, market_data, youtube_data, news_data)

        # 6. 숏폼 파이프라인 (SHORTVIDEO_ENABLED=true 시 실행)
        shorts_result = {}
        if self.config.get("shortvideo", {}).get("enabled"):
            shorts_result = await self._run_shorts_pipeline(dry_run)

        print("✅ 완료\n" + "=" * 60 + "\n")
        return {"analysis": analysis, "stats": stats, "shorts": shorts_result}

    # ── Init ─────────────────────────────────────────────────────────────────

    def _init_components(self) -> None:
        from kstock_signal.collectors.market  import MarketCollector
        from kstock_signal.collectors.news    import NewsCollector
        from kstock_signal.analyzers.trend    import TrendAnalyzer
        from kstock_signal.reporters.telegram import TelegramReporter

        self.market   = MarketCollector(self.config)
        self.news     = NewsCollector(self.config)
        self.analyzer = TrendAnalyzer(self.config)
        self.reporter = TelegramReporter(self.bot) if self.bot else None

        yt_key = self.config.get("youtube_api_key")
        if yt_key:
            from kstock_signal.collectors.youtube import YouTubeCollector
            self.youtube = YouTubeCollector(yt_key, self.config)
            print("✅ YouTube 수집기 활성")
        else:
            self.youtube = None
            print("⚠️  YouTube 수집기 비활성 (API 키 없음)")

        # ── 숏폼 파이프라인 ──────────────────────────────────────────────────
        from kstock_signal.collectors.naver_report   import NaverReportCollector
        from kstock_signal.analyzers.script           import ScriptGenerator
        from kstock_signal.analyzers.celeb_cast       import CelebCaster
        from kstock_signal.generators.ai_video        import AIVideoGenerator
        from kstock_signal.publishers.youtube         import YouTubePublisher

        self.naver_report  = NaverReportCollector(self.config)
        self.script_gen    = ScriptGenerator(self.config)
        self.celeb_caster  = CelebCaster()
        self.video_gen     = AIVideoGenerator(self.config)
        self.yt_publisher  = YouTubePublisher(self.config)

        heygen_key = self.config.get("heygen", {}).get("api_key", "")
        if heygen_key and self.config.get("heygen", {}).get("enabled"):
            from kstock_signal.generators.heygen import HeyGenClient
            self.heygen = HeyGenClient(heygen_key, self.config)
            print("✅ HeyGen 아바타 클라이언트 활성")
        else:
            self.heygen = None
            print("⚠️  HeyGen 비활성 (HEYGEN_API_KEY + heygen.enabled 설정 필요)")

        if yt_key and self.config.get("shortvideo", {}).get("enabled"):
            from kstock_signal.collectors.shortvideo_trend import ShortVideoTrendCollector
            self.trend_collector = ShortVideoTrendCollector(yt_key, self.config)
            print("✅ 숏폼 트렌드 수집기 활성")
        else:
            self.trend_collector = None
            print("⚠️  숏폼 트렌드 수집기 비활성 (SHORTVIDEO_ENABLED=true 설정 필요)")

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

    async def _run_shorts_pipeline(self, dry_run: bool) -> dict:
        """
        숏폼 파이프라인:
          1. 네이버 리포트 수집 + PDF 텍스트 추출
          2. 숏폼 트렌드 패턴 수집 (YouTube API)
          3. LLM 스크립트 생성 (3초 훅 중심)
          4. 영상 생성 (moviepy)
          5. YouTube Shorts 업로드
        """
        print("\n🎬 숏폼 파이프라인 시작")
        result: dict = {"scripts": [], "videos": [], "uploads": []}

        try:
            # 1. 네이버 리포트
            reports = await self.naver_report.collect()
            if not reports:
                print("   ⚠️  수집된 리포트 없음, 숏폼 파이프라인 스킵")
                return result

            # 2. 트렌드 패턴 (API 키 있을 때만)
            trend_patterns: list[dict] = []
            if self.trend_collector:
                trend_patterns = await self.trend_collector.collect()
                if self.db:
                    self._save_trends(trend_patterns)

            # 3. 스크립트 생성 + 영상 제작
            market_data = self.market.collect() if hasattr(self, "market") else {}
            for report in reports:
                # celeb_collab 포맷 — 항상 2명 캐스팅 (매칭 실패 시 상징적 캐릭터 자동 배정)
                celeb_chars = self.celeb_caster.cast(report)
                script = self.script_gen.generate_celeb(
                    report, celeb_chars, trend_patterns, market_data
                )
                print(f"   🎭 캐스트: {' × '.join(c.name for c in celeb_chars)}")

                result["scripts"].append(script.title)

                if self.db:
                    self._save_script(script, report.get("report_id", ""))

                if dry_run:
                    print(f"   [dry-run] 스크립트: {script.hook_text}")
                    for scene in script.scenes:
                        print(f"      [{scene.label}] {scene.character}: {scene.dialogue}")

                # 4. 영상 생성 — celeb_collab + HeyGen 활성 시 아바타 합성
                video_path = None
                if (
                    script.format_type == "celeb_collab"
                    and self.heygen
                    and celeb_chars
                    and all(c.avatar_id for c in celeb_chars)
                ):
                    video_path = await self._run_heygen_collab(script, celeb_chars)

                if not video_path:
                    video_path = self.video_gen.generate(script)

                if video_path:
                    result["videos"].append(video_path)

                    # 5. YouTube 업로드 — dry_run 시 생략
                    if not dry_run:
                        yt_url = self.yt_publisher.upload(video_path, script)
                        if yt_url:
                            result["uploads"].append(yt_url)
                            if self.db:
                                self._save_published_video(script, video_path, yt_url)
                    else:
                        print(f"   [dry-run] 영상 저장: {video_path}")

        except Exception as e:
            print(f"   ⚠️  숏폼 파이프라인 오류: {e}")

        print(f"✅ 숏폼: 스크립트 {len(result['scripts'])}개 · 영상 {len(result['videos'])}개 · 업로드 {len(result['uploads'])}개\n")
        return result

    async def _run_heygen_collab(self, script, celeb_chars: list) -> str | None:
        """
        HeyGen API로 각 캐릭터 대화 씬을 생성 후 moviepy로 합성.

        흐름:
          1. 씬별로 대사를 화자(celeb_char)에 매핑
          2. HeyGen에 각 씬 영상 생성 요청 → video_id 수집
          3. 병렬 폴링 → 완료된 클립 다운로드
          4. moviepy로 순서대로 concatenate
          5. PIL 오버레이(자막/레터박스) 합성
          6. 최종 MP4 경로 반환
        """
        import asyncio
        from pathlib import Path

        try:
            from moviepy import VideoFileClip, concatenate_videoclips
        except ImportError:
            print("   ⚠️  moviepy 미설치 — HeyGen 합성 불가")
            return None

        print("   🎬 HeyGen 아바타 영상 생성 시작...")
        char_map = {c.name: c for c in celeb_chars}
        tmp_dir  = Path("/tmp/heygen_clips")
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # 씬 → (character, dialogue) 매핑
        video_ids: list[tuple[int, str]] = []  # (scene_num, video_id)
        for scene in script.scenes:
            char = char_map.get(scene.character)
            if not char or not scene.dialogue.strip():
                continue

            text = f"{scene.dialogue}"  # HeyGen에 넘길 대사
            vid_id = self.heygen.create_avatar_video(
                avatar_id  = char.avatar_id,
                script_text = text,
                voice_id   = char.voice_id,
                background = "dark_navy",
            )
            if vid_id:
                video_ids.append((scene.scene_num, vid_id))
                print(f"      씬 {scene.scene_num} 생성 요청 OK ({char.name})")

        if not video_ids:
            print("   ⚠️  HeyGen 요청 없음 — PIL fallback")
            return None

        # 폴링 + 다운로드
        clips_order: dict[int, str] = {}
        for scene_num, vid_id in video_ids:
            url = self.heygen.poll_until_done(vid_id)
            if not url:
                continue
            out = str(tmp_dir / f"scene_{scene_num:02d}.mp4")
            if self.heygen.download(url, out):
                clips_order[scene_num] = out
                print(f"      씬 {scene_num} 다운로드 완료")

        if not clips_order:
            print("   ⚠️  다운로드된 클립 없음 — PIL fallback")
            return None

        # moviepy 합성
        ordered = [VideoFileClip(clips_order[k]) for k in sorted(clips_order)]
        final   = concatenate_videoclips(ordered, method="compose")

        safe    = "".join(c if c.isalnum() or c in "-_" else "_" for c in script.stock_name)
        out_path = str(tmp_dir / f"{safe}_celeb_collab.mp4")
        final.write_videofile(out_path, fps=30, codec="libx264", audio=True, logger=None)

        for clip in ordered:
            clip.close()
        final.close()

        print(f"   ✅ HeyGen 합성 완료: {out_path}")
        return out_path

    def _save_trends(self, patterns: list[dict]) -> None:
        try:
            for p in patterns:
                self.db.client.table("shortform_trends").upsert(
                    {
                        "hook_type":        p["hook_type"],
                        "hook_text":        p["hook_text"],
                        "title_format":     p.get("title_format", ""),
                        "engagement_score": p.get("engagement_score", 0),
                        "view_count":       p.get("view_count", 0),
                        "like_count":       p.get("like_count", 0),
                        "comment_count":    p.get("comment_count", 0),
                        "video_id":         p.get("video_id", ""),
                        "channel_title":    p.get("channel_title", ""),
                        "category":         p.get("category", "finance"),
                    },
                    on_conflict="video_id",
                ).execute()
        except Exception as e:
            print(f"   ⚠️  트렌드 DB 저장 실패: {e}")

    def _save_script(self, script, report_id: str) -> None:
        import json as _json
        try:
            self.db.client.table("video_scripts").insert({
                "stock_name":    script.stock_name,
                "hook_type":     script.hook_type,
                "hook_text":     script.hook_text,
                "hook_subtext":  script.hook_subtext,
                "first_frame":   script.first_frame,
                "intro_text":    script.intro_text,
                "body_segments": script.body_segments,
                "subtitles":     script.subtitles,
                "cta_text":      script.cta_text,
                "hashtags":      script.hashtags,
                "title":         script.title,
                "description":   script.description,
                "report_id":     report_id,
            }).execute()
        except Exception as e:
            print(f"   ⚠️  스크립트 DB 저장 실패: {e}")

    def _save_published_video(self, script, file_path: str, url: str) -> None:
        try:
            self.db.client.table("published_videos").insert({
                "platform":  "youtube",
                "video_url": url,
                "file_path": file_path,
                "status":    "uploaded",
            }).execute()
        except Exception as e:
            print(f"   ⚠️  업로드 기록 DB 저장 실패: {e}")

    async def _broadcast(self, analysis, stats, market_data, youtube_data, news_data) -> None:
        recipients = self.config.get("report_recipients", [])
        print(f"📤 발송 ({len(recipients)}명)...")
        for chat_id in recipients:
            await self.reporter.send(chat_id, analysis, stats, market_data, youtube_data, news_data)
            print(f"   ✅ {chat_id}")
