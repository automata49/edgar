from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from database.client import SupabaseDB


def db() -> SupabaseDB:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Supabase is not configured")
    return SupabaseDB(url, key)


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            query = parse_qs(urlparse(self.path).query)
            family_id = query.get("family_id", ["family"])[0] or "family"
            state = db().get_invest_flow_state(family_id)
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
            saved = db().save_invest_flow_state(request.get("payload") or {}, family_id)
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
