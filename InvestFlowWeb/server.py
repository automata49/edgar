#!/usr/bin/env python3
"""Lightweight Invest Flow web server.

Run from the repository root:
    python3 InvestFlowWeb/server.py

This server is only for static hosting and Supabase-backed Invest Flow state.
Heavy yfinance, LLM, YouTube, and PDF jobs remain Telegram-bot-only.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from config import CONFIG as EDGAR_CONFIG
except Exception:  # pragma: no cover - runtime fallback
    EDGAR_CONFIG = {}

try:
    from database.client import SupabaseDB
except Exception:  # pragma: no cover - runtime fallback
    SupabaseDB = None

PORT = int(os.getenv("PORT") or os.getenv("INVEST_FLOW_PORT", "8080"))

LIGHTWEIGHT_MARKET_DATA = {
    "SPY": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
    "QQQ": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
    "BTC": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
    "ETH": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
}


def invest_flow_db() -> SupabaseDB:
    url = EDGAR_CONFIG.get("supabase_url")
    key = EDGAR_CONFIG.get("supabase_key")
    if not SupabaseDB or not url or not key:
        raise RuntimeError("Supabase is not configured")
    return SupabaseDB(url, key)


class InvestFlowHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path)
        if path.path == "/api/market":
            self.send_json({
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "data": LIGHTWEIGHT_MARKET_DATA,
                "status": "mock",
                "note": "Live market collection is reserved for the Telegram bot backend.",
            })
            return
        if path.path == "/api/health":
            self.send_json({
                "ok": True,
                "mode": "lightweight",
                "supabase_state": "/api/investflow/state",
                "heavy_jobs": "telegram-bot-only",
            })
            return
        if path.path == "/api/investflow/state":
            try:
                query = urllib.parse.parse_qs(path.query)
                family_id = query.get("family_id", ["family"])[0] or "family"
                state = invest_flow_db().get_invest_flow_state(family_id)
                self.send_json({
                    "found": bool(state),
                    "family_id": family_id,
                    "payload": state.get("payload") if state else None,
                    "updated_at": state.get("updated_at") if state else None,
                })
            except Exception as exc:
                self.send_json({"error": str(exc)}, status=502)
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path)
        if path.path == "/api/deepseek":
            self.send_json({
                "answer": "",
                "status": "disabled",
                "note": "LLM processing is reserved for the Telegram bot backend.",
            })
            return
        if path.path == "/api/investflow/state":
            try:
                payload = self.read_json_body()
                family_id = str(payload.get("family_id") or "family")
                saved = invest_flow_db().save_invest_flow_state(payload.get("payload") or {}, family_id)
                self.send_json({
                    "ok": True,
                    "family_id": family_id,
                    "updated_at": saved.get("updated_at"),
                })
            except Exception as exc:
                self.send_json({"error": str(exc)}, status=502)
            return
        if path.path != "/api/deepseek":
            self.send_error(404)
            return

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8") or "{}")

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), InvestFlowHandler)
    print(f"Invest Flow server: http://0.0.0.0:{PORT}")
    print("Mode: lightweight static + Supabase state")
    server.serve_forever()


if __name__ == "__main__":
    main()
