from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


TABLE = "invest_flow_states"


def supabase_config() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Supabase is not configured")
    return url.rstrip("/"), key


def supabase_request(path: str, method: str = "GET", payload: dict | None = None) -> dict | list:
    url, key = supabase_config()
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{url}/rest/v1/{path}",
        data=body,
        method=method,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(detail or str(exc)) from exc


def get_state(family_id: str) -> dict | None:
    encoded = urllib.parse.quote(family_id, safe="")
    result = supabase_request(
        f"{TABLE}?family_id=eq.{encoded}&select=family_id,payload,updated_at&limit=1"
    )
    return result[0] if isinstance(result, list) and result else None


def save_state(family_id: str, payload: dict) -> dict:
    result = supabase_request(
        f"{TABLE}?on_conflict=family_id",
        method="POST",
        payload={"family_id": family_id, "payload": payload},
    )
    return result[0] if isinstance(result, list) and result else {}


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            query = parse_qs(urlparse(self.path).query)
            family_id = query.get("family_id", ["family"])[0] or "family"
            state = get_state(family_id)
            self.send_json({
                "found": bool(state),
                "family_id": family_id,
                "payload": state.get("payload") if state else None,
                "updated_at": state.get("updated_at") if state else None,
            })
        except Exception as exc:
            self.send_json({"error": str(exc)}, 502)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            family_id = str(request.get("family_id") or "family")
            saved = save_state(family_id, request.get("payload") or {})
            self.send_json({
                "ok": True,
                "family_id": family_id,
                "updated_at": saved.get("updated_at"),
            })
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
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
