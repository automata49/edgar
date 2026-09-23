from __future__ import annotations

import re
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

    def save_report(self, analysis: str, stats: dict, market_data: dict | None = None,
                    kind: str = "daily") -> int | None:
        main, action = _split_analysis(analysis)
        result = (
            self.client.table("reports")
            .insert({
                "kind":            kind,
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
        """가장 최근 Daily 리포트 (시장 스냅샷 포함)."""
        return self.latest_report_of("daily")

    def recent_news(self, limit: int = 40) -> list[dict]:
        result = (
            self.client.table("news_articles")
            .select("title,url,source,published_at,collected_at")
            .order("collected_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def recent_videos(self, limit: int = 40) -> list[dict]:
        result = (
            self.client.table("youtube_videos")
            .select("title,url,channel,category,published_at,collected_at")
            .order("collected_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    # ── Research Reports (네이버 종목분석) ───────────────────────────────────

    def known_report_ids(self, report_ids: list[str]) -> set[str]:
        ids = [i for i in report_ids if i]
        if not ids:
            return set()
        result = (
            self.client.table("research_reports")
            .select("report_id,summary_model,summary")
            .in_("report_id", ids)
            .execute()
        )
        # 요약에 실패한 리포트는 '아직 처리 안 됨'으로 보고 다음 실행 때 다시 요약합니다
        return {r["report_id"] for r in result.data or [] if not summary_failed(r)}

    def save_research_reports(self, rows: list[dict]) -> int:
        """research_row()로 만든 행을 report_id 기준 upsert."""
        if not rows:
            return 0
        self.client.table("research_reports").upsert(rows, on_conflict="report_id").execute()
        return len(rows)

    def research_stocks(self, limit: int = 60) -> list[dict]:
        """종목별 현황 (stock_research 뷰), 최근 리포트 순."""
        result = (
            self.client.table("stock_research")
            .select("*")
            .order("last_report_day", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def research_by_stock(self, stock: str, limit: int = 10) -> list[dict]:
        """종목코드(6자리) 또는 종목명(부분 일치)으로 최근 리포트."""
        q = self.client.table("research_reports").select(_RESEARCH_COLUMNS)
        q = q.eq("stock_code", stock) if re.fullmatch(r"\w{6}", stock) and any(c.isdigit() for c in stock) \
            else q.ilike("stock_name", f"%{stock}%")
        result = q.order("report_day", desc=True).order("id", desc=True).limit(limit).execute()
        return result.data or []

    def research_since(self, since_iso: str, limit: int = 300) -> list[dict]:
        result = (
            self.client.table("research_reports")
            .select(_RESEARCH_COLUMNS)
            .gte("collected_at", since_iso)
            .order("report_day", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    # ── Weekly 집계용 조회 ─────────────────────────────────────────────────

    def market_since(self, since_iso: str, limit: int = 5000) -> list[dict]:
        result = (
            self.client.table("market_data")
            .select("symbol,category,price,change_pct,collected_at")
            .gte("collected_at", since_iso)
            .order("collected_at")
            .limit(limit)
            .execute()
        )
        return result.data or []

    def news_since(self, since_iso: str, limit: int = 500) -> list[dict]:
        result = (
            self.client.table("news_articles")
            .select("title,url,source,published_at,collected_at")
            .gte("collected_at", since_iso)
            .order("collected_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def reports_since(self, since_iso: str, kind: str = "daily") -> list[dict]:
        result = (
            self.client.table("reports")
            .select("id,kind,analysis,action_plan,created_at")
            .eq("kind", kind)
            .gte("created_at", since_iso)
            .order("created_at")
            .execute()
        )
        return result.data or []

    def latest_report_of(self, kind: str) -> dict | None:
        result = (
            self.client.table("reports")
            .select("*")
            .eq("kind", kind)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None


_RESEARCH_COLUMNS = ("report_id,stock_name,stock_code,firm,title,report_day,opinion,target_value,"
                     "target_change,sentiment,summary,summary_model,pdf_url,collected_at")


def summary_failed(row: dict) -> bool:
    """모델 호출 실패로 저장된 행인지 (PDF 본문이 없던 경우는 재시도해도 같으므로 제외)."""
    status = str((row.get("summary") or {}).get("status") or "")
    return row.get("summary_model") is None and status.startswith("요약 실패") and "PDF 본문 없음" not in status


def research_row(report: dict, summary: dict) -> dict:
    """수집기 리포트 + 요약 → research_reports 행."""
    return {
        "report_id":     report.get("report_id") or None,
        "stock_name":    report.get("stock_name", ""),
        "stock_code":    report.get("stock_code") or None,
        "firm":          report.get("firm", ""),
        "title":         report.get("title", ""),
        "report_date":   report.get("date", ""),
        "report_day":    report.get("report_day"),
        "pdf_url":       report.get("pdf_url", ""),
        "text_content":  (report.get("text") or "")[:20000],
        "key_numbers":   report.get("key_numbers") or [],
        "opinion":       summary.get("opinion"),
        "target_value":  summary.get("target_price"),
        "target_price":  f"{summary['target_price']:,}원" if summary.get("target_price") else "",
        "target_change": summary.get("target_change"),
        "sentiment":     summary.get("sentiment"),
        "summary":       {k: summary.get(k) for k in ("one_line", "opinion_change", "current_price",
                                                       "key_points", "risks", "numbers", "status")},
        "summary_model": summary.get("model"),
        "collected_at":  datetime.now(timezone.utc).isoformat(),
    }


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
