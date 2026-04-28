from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build


class YouTubeCollector:
    """YouTube 채널 + 플레이리스트 수집 (자막 포함)."""

    def __init__(self, api_key: str, config: dict) -> None:
        self.yt = build("youtube", "v3", developerKey=api_key)
        self.channels: dict[str, list[str]] = config.get("youtube_channels", {})
        self.hours: int = config.get("collection_timeframes", {}).get("youtube", 24)

    async def collect(self) -> list[dict]:
        all_videos: list[dict] = []

        for category, urls in self.channels.items():
            for url in urls:
                videos = self._collect_source(url, category)
                all_videos.extend(videos)

        print(f"   📊 YouTube 총 {len(all_videos)}개\n")
        return self._add_transcripts(all_videos)

    # ── Private ──────────────────────────────────────────────────────────────

    def _collect_source(self, url: str, category: str) -> list[dict]:
        if "playlist?list=" in url:
            return self._playlist_videos(url.split("list=")[1].split("&")[0], category)
        channel_id = self._resolve_channel_id(url)
        return self._channel_videos(channel_id, category) if channel_id else []

    def _resolve_channel_id(self, url: str) -> str | None:
        if "/channel/" in url:
            return url.split("/channel/")[1].split("/")[0]
        if "/@" in url:
            username = url.split("/@")[1].split("/")[0]
            try:
                resp = self.yt.search().list(part="snippet", q=username, type="channel", maxResults=1).execute()
                if resp.get("items"):
                    return resp["items"][0]["snippet"]["channelId"]
            except Exception:
                pass
        return None

    def _channel_videos(self, channel_id: str, category: str, max_results: int = 3) -> list[dict]:
        try:
            resp = self.yt.search().list(
                part="snippet",
                channelId=channel_id,
                order="date",
                type="video",
                maxResults=max_results,
            ).execute()
            return [self._parse_item(item, category) for item in resp.get("items", [])]
        except Exception as e:
            print(f"   ⚠️  channel {channel_id}: {str(e)[:60]}")
            return []

    def _playlist_videos(self, playlist_id: str, category: str, max_results: int = 3) -> list[dict]:
        try:
            resp = self.yt.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=max_results,
            ).execute()
            return [self._parse_playlist_item(item, category) for item in resp.get("items", [])]
        except Exception as e:
            print(f"   ⚠️  playlist {playlist_id}: {str(e)[:60]}")
            return []

    def _parse_item(self, item: dict, category: str) -> dict:
        snippet = item.get("snippet", {})
        vid_id  = item.get("id", {}).get("videoId", "")
        return {
            "video_id":     vid_id,
            "title":        snippet.get("title", ""),
            "url":          f"https://www.youtube.com/watch?v={vid_id}",
            "channel_name": snippet.get("channelTitle", ""),
            "category":     category,
            "description":  snippet.get("description", "")[:500],
            "published_at": snippet.get("publishedAt"),
            "transcript":   "",
        }

    def _parse_playlist_item(self, item: dict, category: str) -> dict:
        snippet = item.get("snippet", {})
        res     = snippet.get("resourceId", {})
        vid_id  = res.get("videoId", "")
        return {
            "video_id":     vid_id,
            "title":        snippet.get("title", ""),
            "url":          f"https://www.youtube.com/watch?v={vid_id}",
            "channel_name": snippet.get("channelTitle", ""),
            "category":     category,
            "description":  snippet.get("description", "")[:500],
            "published_at": snippet.get("publishedAt"),
            "transcript":   "",
        }

    def _add_transcripts(self, videos: list[dict]) -> list[dict]:
        for v in videos:
            v["transcript"] = v.get("description", "")[:1000]
        return videos

    def _yt_dlp_transcript(self, video_id: str) -> str | None:
        """yt-dlp 자막 추출 (느리므로 기본 비활성화, 필요시 호출)."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--skip-download", "--write-auto-sub", "--sub-lang", "ko,en",
                 "--sub-format", "json3", "--print", "%(subtitles)s",
                 f"https://www.youtube.com/watch?v={video_id}"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout[:3000]
        except Exception:
            pass
        return None
