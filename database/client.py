from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client, create_client


class SupabaseDB:
    """Edgar 데이터 저장소."""

    def __init__(self, url: str, key: str) -> None:
        self.client: Client = create_client(url, key)

    # ── Market Data ──────────────────────────────────────────────────────────

    def save_market_data(self, market_data: dict, category_map: dict | None = None) -> int:
        if not market_data:
            return 0
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            {
                "symbol":       symbol,
                "category":     (category_map or {}).get(symbol, "unknown"),
                "price":        data.get("price"),
                "change":       data.get("change"),
                "change_pct":   data.get("change_percent"),
                "prev_close":   data.get("previous_close"),
                "collected_at": now,
            }
            for symbol, data in market_data.items()
        ]
        self.client.table("market_data").insert(rows).execute()
        return len(rows)

    # ── YouTube ──────────────────────────────────────────────────────────────

    def save_youtube_videos(self, videos: list) -> int:
        if not videos:
            return 0
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            {
                "video_id":     v.get("video_id") or _video_id_from_url(v.get("url", "")),
                "title":        v.get("title", ""),
                "url":          v.get("url", ""),
                "channel":      v.get("channel_name") or v.get("channel", ""),
                "category":     v.get("category", ""),
                "transcript":   v.get("transcript", ""),
                "published_at": v.get("published_at"),
                "collected_at": now,
            }
            for v in videos
        ]
        self.client.table("youtube_videos").upsert(
            rows, on_conflict="video_id", ignore_duplicates=True
        ).execute()
        return len(rows)

    # ── News ─────────────────────────────────────────────────────────────────

    def save_news_articles(self, articles: list) -> int:
        if not articles:
            return 0
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            {
                "title":        a.get("title", ""),
                "url":          a["url"],
                "source":       a.get("source", ""),
                "summary":      a.get("summary", ""),
                "published_at": a.get("published"),
                "collected_at": now,
            }
            for a in articles
            if a.get("url")
        ]
        self.client.table("news_articles").upsert(
            rows, on_conflict="url", ignore_duplicates=True
        ).execute()
        return len(rows)

    # ── Reports ──────────────────────────────────────────────────────────────

    def save_report(self, analysis: str, stats: dict, market_data: dict | None = None) -> int | None:
        main, action = _split_analysis(analysis)
        result = (
            self.client.table("reports")
            .insert({
                "analysis":        main,
                "action_plan":     action,
                "youtube_count":   stats.get("youtube_count", 0),
                "website_count":   stats.get("website_count", 0),
                "market_snapshot": market_data or {},
                "created_at":      datetime.now(timezone.utc).isoformat(),
            })
            .execute()
        )
        return result.data[0]["id"] if result.data else None

    def latest_report(self) -> dict | None:
        result = (
            self.client.table("reports")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _video_id_from_url(url: str) -> str | None:
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return None


def _split_analysis(text: str) -> tuple[str, str | None]:
    if "액션 플랜:" in text:
        parts = text.split("액션 플랜:", 1)
        return parts[0].strip(), parts[1].strip()
    return text.strip(), None
