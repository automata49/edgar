from __future__ import annotations

import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler


def call_deepseek(messages: list[dict], report_context: str = "") -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    system_prompt = (
        "당신은 금융 트렌드 분석 전문가입니다. 최신 시장 데이터와 사용자 메모를 바탕으로 "
        "간결하고 실행 가능한 투자 검토 메모를 작성하세요.\n\n"
        f"=== 최신 리포트 ===\n{report_context[:3000] if report_context else '리포트 없음'}"
    )
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "temperature": 0.7,
        "max_tokens": 1000,
    }
    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            answer = call_deepseek(payload.get("messages", []), payload.get("report_context", ""))
            self.send_json({"answer": answer})
        except Exception as exc:
            self.send_json({"error": str(exc)}, 502)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
