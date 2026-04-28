from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


class YouTubePublisher:
    """
    YouTube Shorts 업로드.

    인증: OAuth 2.0 (client_secrets.json → token 파일 캐시)
    첫 실행 시 브라우저 인증 URL 출력 → 코드 입력 필요.
    """

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    def __init__(self, config: dict) -> None:
        cfg                    = config.get("youtube_shorts", {})
        self.client_secrets    = cfg.get("client_secrets_file", "")
        self.credentials_file  = cfg.get("credentials_file", "/tmp/yt_credentials.json")
        self.category_id       = cfg.get("category_id", "22")
        self.privacy_status    = cfg.get("privacy_status", "public")
        self._service          = None

    def upload(self, video_path: str, script) -> Optional[str]:
        """
        MP4 업로드 후 YouTube URL 반환.
        실패 시 None 반환.
        """
        if not os.path.exists(video_path):
            print(f"   ⚠️  업로드 파일 없음: {video_path}")
            return None

        service = self._get_service()
        if not service:
            return None

        try:
            return self._do_upload(service, video_path, script)
        except Exception as e:
            print(f"   ⚠️  YouTube 업로드 실패: {e}")
            return None

    # ── Upload ───────────────────────────────────────────────────────────────

    def _do_upload(self, service, video_path: str, script) -> str:
        from googleapiclient.http import MediaFileUpload

        tags = [t.lstrip("#") for t in script.hashtags] + ["Shorts"]

        body = {
            "snippet": {
                "title":       script.title[:100],
                "description": script.description + "\n\n" + " ".join(script.hashtags),
                "tags":        tags,
                "categoryId":  self.category_id,
            },
            "status": {
                "privacyStatus":         self.privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5,  # 5 MB chunks
        )

        request  = service.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"   📤 업로드 {pct}%", end="\r")

        vid_id = response.get("id", "")
        url    = f"https://youtube.com/shorts/{vid_id}"
        print(f"\n   ✅ YouTube Shorts 업로드 완료: {url}")
        return url

    # ── OAuth ────────────────────────────────────────────────────────────────

    def _get_service(self):
        if self._service:
            return self._service
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            print("   ⚠️  google-auth-oauthlib 미설치. pip install google-auth-oauthlib 실행 필요")
            return None

        creds = None
        if os.path.exists(self.credentials_file):
            with open(self.credentials_file) as f:
                creds = Credentials.from_authorized_user_info(json.load(f), self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.client_secrets or not os.path.exists(self.client_secrets):
                    print(
                        "   ⚠️  YouTube OAuth: client_secrets.json 없음\n"
                        "   → Google Cloud Console에서 OAuth 2.0 자격증명 생성 후\n"
                        "     YOUTUBE_CLIENT_SECRETS 환경변수에 경로 설정\n"
                        "   참고: https://console.cloud.google.com/apis/credentials"
                    )
                    return None
                flow  = InstalledAppFlow.from_client_secrets_file(self.client_secrets, self.SCOPES)
                creds = flow.run_local_server(port=0)

            with open(self.credentials_file, "w") as f:
                f.write(creds.to_json())

        self._service = build("youtube", "v3", credentials=creds)
        return self._service
