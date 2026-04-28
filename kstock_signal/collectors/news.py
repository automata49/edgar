from __future__ import annotations

from datetime import datetime, timedelta

import feedparser


class NewsCollector:
    """RSS 피드 뉴스 수집."""

    def __init__(self, config: dict) -> None:
        self.feeds: list[str] = config.get("rss_feeds", [])
        self.hours: int = config.get("collection_timeframes", {}).get("website", 24)

    async def collect(self) -> list[dict]:
        cutoff = datetime.now() - timedelta(hours=self.hours)
        articles: list[dict] = []

        for url in self.feeds:
            articles.extend(self._parse_feed(url, cutoff))

        print(f"   📡 뉴스/RSS: {len(articles)}개\n")
        return articles

    # ── Private ──────────────────────────────────────────────────────────────

    def _parse_feed(self, url: str, cutoff: datetime) -> list[dict]:
        try:
            feed = feedparser.parse(url)
            source = feed.feed.get("title", url.split("/")[2] if "/" in url else url)
            result = []

            for entry in feed.entries[:20]:
                published = self._parse_date(entry)
                if published and published < cutoff:
                    continue
                link = entry.get("link", "")
                if not link:
                    continue
                result.append({
                    "title":    entry.get("title", "No title"),
                    "url":      link,
                    "summary":  entry.get("summary", "")[:300],
                    "source":   source,
                    "published": published.isoformat() if published else None,
                })

            return result[:10]
        except Exception as e:
            domain = url.split("/")[2] if "/" in url else url
            print(f"   ⚠️  RSS {domain}: {str(e)[:50]}")
            return []

    @staticmethod
    def _parse_date(entry) -> datetime | None:
        for attr in ("published_parsed", "updated_parsed"):
            val = getattr(entry, attr, None)
            if val:
                try:
                    return datetime(*val[:6])
                except Exception:
                    pass
        return None
