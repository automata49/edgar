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


# ── AppLovin-style: 실시간 engagement 기반 트렌드 수집 ───────────────────────

class ShortVideoTrendCollector:
    """
    YouTube Data API로 금융/투자 숏폼 트렌드를 수집.

    수집 로직:
    - 최신 Shorts (< 60초, 세로형) 중 금융 관련 채널 검색
    - engagement_score = views * 0.4 + likes * 30 + comments * 20  (AXON 가중치)
    - hook_type 자동 분류 후 DB 저장
    """

    SEARCH_QUERIES = [
        "주식 shorts 오늘",
        "주식 투자 숏폼",
        "코스피 shorts",
        "삼성전자 주가 shorts",
        "미국주식 shorts",
        "ETF 투자 shorts",
        "재테크 shorts",
    ]

    def __init__(self, api_key: str, config: dict) -> None:
        self.api_key = api_key
        self.max_results = config.get("shortvideo", {}).get("trend_max_results", 10)

    async def collect(self) -> list[dict]:
        print("📱 숏폼 트렌드 수집 중...")
        try:
            from googleapiclient.discovery import build
        except ImportError:
            print("   ⚠️  google-api-python-client 미설치")
            return []

        service = build("youtube", "v3", developerKey=self.api_key)
        patterns: list[TrendPattern] = []

        for query in self.SEARCH_QUERIES:
            items = self._search(service, query)
            for item in items:
                vid_id = item.get("id", {}).get("videoId", "")
                if not vid_id:
                    continue
                stats = self._get_stats(service, vid_id)
                if not stats:
                    continue

                snippet = item.get("snippet", {})
                pattern = self._build_pattern(vid_id, snippet, stats)
                if pattern:
                    patterns.append(pattern)

        # engagement_score 상위 정렬
        patterns.sort(key=lambda p: p.engagement_score, reverse=True)
        top = patterns[:20]

        print(f"✅ 숏폼 트렌드: {len(top)}개 패턴 수집\n")
        return [self._to_dict(p) for p in top]

    # ── YouTube API Calls ────────────────────────────────────────────────────

    def _search(self, service, query: str) -> list[dict]:
        try:
            published_after = (datetime.now(timezone.utc) - timedelta(hours=72)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            resp = service.search().list(
                part="snippet",
                q=query,
                type="video",
                videoDuration="short",
                order="viewCount",
                publishedAfter=published_after,
                maxResults=self.max_results,
                regionCode="KR",
                relevanceLanguage="ko",
            ).execute()
            return resp.get("items", [])
        except Exception as e:
            print(f"   ⚠️  YouTube 검색 오류 ({query}): {e}")
            return []

    def _get_stats(self, service, video_id: str) -> Optional[dict]:
        try:
            resp = service.videos().list(
                part="statistics,contentDetails",
                id=video_id,
            ).execute()
            items = resp.get("items", [])
            if not items:
                return None
            return {
                "statistics":     items[0].get("statistics", {}),
                "contentDetails": items[0].get("contentDetails", {}),
            }
        except Exception:
            return None

    # ── Pattern Building ─────────────────────────────────────────────────────

    def _build_pattern(self, vid_id: str, snippet: dict, stats: dict) -> Optional[TrendPattern]:
        s = stats.get("statistics", {})
        views    = int(s.get("viewCount", 0))
        likes    = int(s.get("likeCount", 0))
        comments = int(s.get("commentCount", 0))

        # 최소 노출 필터 (10만 뷰 미만 제외)
        if views < 100_000:
            return None

        # AXON-style engagement score
        score = views * 0.4 + likes * 30 + comments * 20

        title = snippet.get("title", "")
        hook_type = self._classify_hook(title)

        return TrendPattern(
            hook_type        = hook_type,
            hook_text        = self._extract_hook_phrase(title),
            title_format     = self._normalize_title_format(title),
            engagement_score = score,
            view_count       = views,
            like_count       = likes,
            comment_count    = comments,
            video_id         = vid_id,
            channel_title    = snippet.get("channelTitle", ""),
            published_at     = snippet.get("publishedAt", ""),
        )

    # ── Hook Classification (Zeta-style intent 분류) ─────────────────────────

    def _classify_hook(self, title: str) -> str:
        """제목에서 훅 유형 분류."""
        if re.search(r"[?？]", title):
            return "question"
        if re.search(r"\d+[%％배]|\d+억|\d+조", title):
            return "shock_stat"
        if re.search(r"(급등|폭등|급락|붕괴|위기|폭발|역대)", title):
            return "bold_claim"
        if re.search(r"(가지|이유|방법|비결|[①②③]|\d+[가지위번])", title):
            return "listicle"
        return "bold_claim"

    def _extract_hook_phrase(self, title: str) -> str:
        """제목의 첫 20자를 훅 문구로 추출."""
        clean = re.sub(r"[#\[\]]", "", title).strip()
        return clean[:40]

    def _normalize_title_format(self, title: str) -> str:
        """숫자를 {N}으로 치환해 재사용 가능한 포맷으로 변환."""
        fmt = re.sub(r"\d+[%％]", "{PCT}%", title)
        fmt = re.sub(r"\d+억", "{N}억", fmt)
        fmt = re.sub(r"\d+조", "{N}조", fmt)
        fmt = re.sub(r"\d{4,}", "{PRICE}", fmt)
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
