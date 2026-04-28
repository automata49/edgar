from __future__ import annotations

import time
from pathlib import Path
from typing import Optional


class HeyGenClient:
    """
    HeyGen API 클라이언트 — AI 아바타 숏폼 영상 생성.

    설정 (config["heygen"]):
      api_key    : HeyGen API 키
      enabled    : true/false
      poll_sleep : 폴링 간격(초, 기본 10)
      timeout    : 최대 대기(초, 기본 300)
    """

    _BASE = "https://api.heygen.com"

    def __init__(self, api_key: str, config: dict | None = None) -> None:
        self.api_key    = api_key
        cfg             = (config or {}).get("heygen", {})
        self.poll_sleep = int(cfg.get("poll_sleep", 10))
        self.timeout    = int(cfg.get("timeout", 300))
        self._headers   = {
            "X-Api-Key":    api_key,
            "Content-Type": "application/json",
        }

    # ── 영상 생성 요청 ────────────────────────────────────────────────────────

    def create_avatar_video(
        self,
        avatar_id:  str,
        script_text: str,
        voice_id:   str = "",
        background: str = "dark_navy",
    ) -> Optional[str]:
        """
        아바타 영상 생성 요청.

        Returns:
            video_id (str) — 폴링에 사용. None이면 실패.
        """
        import requests

        payload = {
            "video_inputs": [{
                "character": {
                    "type":         "avatar",
                    "avatar_id":    avatar_id,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type":       "text",
                    "input_text": script_text[:500],
                    "voice_id":   voice_id or self._default_voice(),
                },
                "background": {
                    "type":  "color",
                    "value": self._bg_hex(background),
                },
            }],
            "dimension":    {"width": 720, "height": 1280},
            "aspect_ratio": "9:16",
        }

        try:
            r = requests.post(
                f"{self._BASE}/v2/video/generate",
                headers=self._headers,
                json=payload,
                timeout=30,
            )
            r.raise_for_status()
            return r.json().get("data", {}).get("video_id")
        except Exception as e:
            print(f"   ⚠️  HeyGen 생성 요청 실패: {e}")
            return None

    # ── 완료 폴링 ─────────────────────────────────────────────────────────────

    def poll_until_done(self, video_id: str) -> Optional[str]:
        """
        영상 완료까지 폴링.

        Returns:
            video_url (str) — 완료 시 다운로드 URL. None이면 실패/타임아웃.
        """
        import requests

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                r = requests.get(
                    f"{self._BASE}/v1/video_status.get",
                    params={"video_id": video_id},
                    headers=self._headers,
                    timeout=10,
                )
                data   = r.json().get("data", {})
                status = data.get("status", "")
                if status == "completed":
                    return data.get("video_url")
                if status == "failed":
                    print(f"   ⚠️  HeyGen 렌더링 실패: {data.get('error')}")
                    return None
            except Exception as e:
                print(f"   ⚠️  HeyGen 폴링 오류: {e}")
            time.sleep(self.poll_sleep)

        print("   ⚠️  HeyGen 타임아웃")
        return None

    # ── 다운로드 ──────────────────────────────────────────────────────────────

    def download(self, video_url: str, output_path: str) -> bool:
        """HeyGen 생성 영상을 로컬에 다운로드."""
        import requests

        try:
            r = requests.get(video_url, stream=True, timeout=120)
            r.raise_for_status()
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            print(f"   ⚠️  HeyGen 다운로드 실패: {e}")
            return False

    # ── 내부 유틸 ─────────────────────────────────────────────────────────────

    def _default_voice(self) -> str:
        return "en-US-GuyNeural"

    def _bg_hex(self, name: str) -> str:
        return {
            "dark_navy": "#050514",
            "black":     "#080808",
            "deep_blue": "#0A0A2E",
        }.get(name, "#050514")
