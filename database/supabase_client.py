from supabase import create_client, Client
from datetime import datetime, timezone


class SupabaseDB:
    """Edgar 데이터 저장소 (Supabase/PostgreSQL)"""

    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    # ─── 시장 데이터 ────────────────────────────────────────────────

    def save_market_data(self, market_data: dict, category_map: dict | None = None) -> int:
        """시장 데이터 저장. category_map은 symbol→category 매핑."""
        if not market_data:
            return 0

        rows = []
        for symbol, data in market_data.items():
            rows.append({
                "symbol":       symbol,
                "category":     (category_map or {}).get(symbol, "unknown"),
                "price":        data.get("price"),
                "change":       data.get("change"),
                "change_pct":   data.get("change_percent"),
                "prev_close":   data.get("previous_close"),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })

        self.client.table("market_data").insert(rows).execute()
        return len(rows)

    # ─── YouTube ────────────────────────────────────────────────────

    def save_youtube_videos(self, videos: list) -> int:
        """YouTube 영상 저장 (중복 video_id는 무시)."""
        if not videos:
            return 0

        rows = []
        for v in videos:
            video_id = v.get("video_id") or v.get("id") or _extract_video_id(v.get("url", ""))
            rows.append({
                "video_id":     video_id,
                "title":        v.get("title", ""),
                "url":          v.get("url", ""),
                "channel":      v.get("channel_name") or v.get("channel", ""),
                "category":     v.get("category", ""),
                "transcript":   v.get("transcript", ""),
                "published_at": v.get("published_at"),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })

        # on_conflict: video_id 중복이면 skip
        self.client.table("youtube_videos").upsert(rows, on_conflict="video_id", ignore_duplicates=True).execute()
        return len(rows)

    # ─── 뉴스/RSS ────────────────────────────────────────────────────

    def save_news_articles(self, articles: list) -> int:
        """뉴스 기사 저장 (URL 중복은 무시)."""
        if not articles:
            return 0

        rows = []
        for a in articles:
            if not a.get("url"):
                continue
            rows.append({
                "title":        a.get("title", ""),
                "url":          a.get("url"),
                "source":       a.get("source", ""),
                "summary":      a.get("summary", ""),
                "published_at": a.get("published"),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })

        self.client.table("news_articles").upsert(rows, on_conflict="url", ignore_duplicates=True).execute()
        return len(rows)

    # ─── 리포트 ─────────────────────────────────────────────────────

    def save_report(self, analysis: str, stats: dict, market_data: dict | None = None) -> int | None:
        """AI 분석 리포트 저장. 저장된 row의 id를 반환."""
        action_plan = None
        main_analysis = analysis

        if "액션 플랜:" in analysis:
            parts = analysis.split("액션 플랜:", 1)
            main_analysis = parts[0].strip()
            action_plan = parts[1].strip()

        result = (
            self.client.table("reports")
            .insert({
                "analysis":        main_analysis,
                "action_plan":     action_plan,
                "youtube_count":   stats.get("youtube_count", 0),
                "website_count":   stats.get("website_count", 0),
                "market_snapshot": market_data or {},
                "created_at":      datetime.now(timezone.utc).isoformat(),
            })
            .execute()
        )
        return result.data[0]["id"] if result.data else None


# ─── 헬퍼 ────────────────────────────────────────────────────────────

def _extract_video_id(url: str) -> str | None:
    """YouTube URL에서 video_id 추출."""
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return None
