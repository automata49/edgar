from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class TrendPattern:
    """숏폼 트렌드 패턴 단위."""
    hook_type:        str          # question / shock_stat / bold_claim / listicle
    hook_text:        str          # 실제 훅 문구 예시
    title_format:     str          # 제목 패턴
    engagement_score: float = 0.0  # 좋아요+댓글+공유 합산 지수
    view_count:       int   = 0
    like_count:       int   = 0
    comment_count:    int   = 0
    video_id:         str   = ""
    channel_title:    str   = ""
    published_at:     str   = ""
    category:         str   = "finance"


# ── Query categories ─────────────────────────────────────────────────────────

_SEARCH_QUERIES: dict[str, list[str]] = {
    "finance_ko": [
        "주식 shorts 오늘",
        "주식 급등 숏츠",
        "코스피 shorts",
        "삼성전자 주가 shorts",
        "미국주식 shorts",
        "ETF 투자 shorts",
        "재테크 shorts",
        "주식 투자 비법 shorts",
    ],
    "finance_en": [
        "stock market shorts today",
        "investing tips shorts",
        "crypto shorts viral",
        "wall street bets shorts",
    ],
    "viral_ko": [
        "충격적인 사실 shorts",
        "알고보면 shorts",
        "이걸 몰랐다면 shorts",
        "반전있는 shorts",
    ],
}


class ShortVideoTrendCollector:
    """
    YouTube Data API로 금융/투자 숏폼 트렌드를 수집.

    수집 로직:
    1. YouTube chart=mostPopular (카테고리 25=News/24=Entertainment/22=People) 트렌딩 영상
    2. 금융·투자·바이럴 키워드 검색 (한/영)
    3. engagement_score = views * 0.4 + likes * 30 + comments * 20  (AXON 가중치)
    4. hook_type 자동 분류
    """

    def __init__(self, api_key: str, config: dict) -> None:
        self.api_key     = api_key
        self.max_results = config.get("shortvideo", {}).get("trend_max_results", 10)

    async def collect(self) -> list[dict]:
        print("📱 숏폼 트렌드 수집 중...")
        try:
            from googleapiclient.discovery import build
        except ImportError:
            print("   ⚠️  google-api-python-client 미설치")
            return []

        service  = build("youtube", "v3", developerKey=self.api_key)
        patterns: list[TrendPattern] = []

        # 1. YouTube Trending (mostPopular) — 한국 기준
        patterns.extend(self._collect_trending(service))

        # 2. 키워드 검색 (카테고리별)
        for category, queries in _SEARCH_QUERIES.items():
            for query in queries:
                items = self._search(service, query)
                for item in items:
                    vid_id = item.get("id", {}).get("videoId", "")
                    if not vid_id:
                        continue
                    stats = self._get_stats(service, vid_id)
                    if not stats:
                        continue
                    snippet = item.get("snippet", {})
                    p = self._build_pattern(vid_id, snippet, stats, category)
                    if p:
                        patterns.append(p)

        # engagement_score 상위 정렬
        patterns.sort(key=lambda p: p.engagement_score, reverse=True)
        top = patterns[:20]

        print(f"✅ 숏폼 트렌드: {len(top)}개 패턴 수집\n")
        return [self._to_dict(p) for p in top]

    # ── YouTube Trending ─────────────────────────────────────────────────────

    def _collect_trending(self, service) -> list[TrendPattern]:
        """YouTube mostPopular 차트에서 트렌딩 영상 수집."""
        patterns: list[TrendPattern] = []
        # 25=News, 24=Entertainment, 22=People&Blogs
        for cat_id in ("25", "24", "22"):
            try:
                resp = service.videos().list(
                    part           = "snippet,statistics,contentDetails",
                    chart          = "mostPopular",
                    regionCode     = "KR",
                    videoCategoryId= cat_id,
                    maxResults     = 15,
                ).execute()
                for item in resp.get("items", []):
                    p = self._build_pattern_from_video(item, "trending")
                    if p:
                        patterns.append(p)
            except Exception as e:
                print(f"   ⚠️  Trending [{cat_id}] 오류: {e}")
        return patterns

    def _build_pattern_from_video(self, item: dict, category: str) -> Optional[TrendPattern]:
        """videos().list() 응답 아이템에서 직접 패턴 빌드."""
        vid_id   = item.get("id", "")
        snippet  = item.get("snippet", {})
        s        = item.get("statistics", {})
        views    = int(s.get("viewCount",   0))
        likes    = int(s.get("likeCount",   0))
        comments = int(s.get("commentCount", 0))

        if views < 50_000:
            return None

        score     = views * 0.4 + likes * 30 + comments * 20
        title     = snippet.get("title", "")

        return TrendPattern(
            hook_type        = self._classify_hook(title),
            hook_text        = self._extract_hook_phrase(title),
            title_format     = self._normalize_title_format(title),
            engagement_score = score,
            view_count       = views,
            like_count       = likes,
            comment_count    = comments,
            video_id         = vid_id,
            channel_title    = snippet.get("channelTitle", ""),
            published_at     = snippet.get("publishedAt",  ""),
            category         = category,
        )

    # ── Search ───────────────────────────────────────────────────────────────

    def _search(self, service, query: str) -> list[dict]:
        try:
            published_after = (datetime.now(timezone.utc) - timedelta(hours=72)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            resp = service.search().list(
                part           = "snippet",
                q              = query,
                type           = "video",
                videoDuration  = "short",
                order          = "viewCount",
                publishedAfter = published_after,
                maxResults     = self.max_results,
                regionCode     = "KR",
            ).execute()
            return resp.get("items", [])
        except Exception as e:
            print(f"   ⚠️  YouTube 검색 오류 ({query}): {e}")
            return []

    def _get_stats(self, service, video_id: str) -> Optional[dict]:
        try:
            resp  = service.videos().list(
                part="statistics,contentDetails",
                id=video_id,
            ).execute()
            items = resp.get("items", [])
            return {"statistics": items[0].get("statistics", {})} if items else None
        except Exception:
            return None

    # ── Pattern Building ─────────────────────────────────────────────────────

    def _build_pattern(
        self,
        vid_id: str,
        snippet: dict,
        stats: dict,
        category: str = "finance",
    ) -> Optional[TrendPattern]:
        s        = stats.get("statistics", {})
        views    = int(s.get("viewCount",   0))
        likes    = int(s.get("likeCount",   0))
        comments = int(s.get("commentCount", 0))

        if views < 100_000:
            return None

        score = views * 0.4 + likes * 30 + comments * 20
        title = snippet.get("title", "")

        return TrendPattern(
            hook_type        = self._classify_hook(title),
            hook_text        = self._extract_hook_phrase(title),
            title_format     = self._normalize_title_format(title),
            engagement_score = score,
            view_count       = views,
            like_count       = likes,
            comment_count    = comments,
            video_id         = vid_id,
            channel_title    = snippet.get("channelTitle", ""),
            published_at     = snippet.get("publishedAt",  ""),
            category         = category,
        )

    # ── Hook Classification ──────────────────────────────────────────────────

    def _classify_hook(self, title: str) -> str:
        if re.search(r"[?？]", title):
            return "question"
        if re.search(r"\d+[%％배]|\d+억|\d+조|\d+%", title):
            return "shock_stat"
        if re.search(r"(급등|폭등|급락|붕괴|위기|폭발|역대|충격|반전|shocking|surged|crashed)", title, re.I):
            return "bold_claim"
        if re.search(r"(가지|이유|방법|비결|[①②③]|\d+[가지위번]|tips|reasons|ways)", title, re.I):
            return "listicle"
        return "bold_claim"

    def _extract_hook_phrase(self, title: str) -> str:
        clean = re.sub(r"[#\[\]【】]", "", title).strip()
        return clean[:40]

    def _normalize_title_format(self, title: str) -> str:
        fmt = re.sub(r"\d+[%％]",  "{PCT}%", title)
        fmt = re.sub(r"\d+억",     "{N}억",   fmt)
        fmt = re.sub(r"\d+조",     "{N}조",   fmt)
        fmt = re.sub(r"\d{4,}",   "{PRICE}", fmt)
        return fmt[:80]

    def _to_dict(self, p: TrendPattern) -> dict:
        return {
            "hook_type":        p.hook_type,
            "hook_text":        p.hook_text,
            "title_format":     p.title_format,
            "engagement_score": round(p.engagement_score),
            "view_count":       p.view_count,
            "like_count":       p.like_count,
            "comment_count":    p.comment_count,
            "video_id":         p.video_id,
            "channel_title":    p.channel_title,
            "published_at":     p.published_at,
            "category":         p.category,
            "collected_at":     datetime.now().isoformat(),
        }
