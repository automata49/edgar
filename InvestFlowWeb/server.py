#!/usr/bin/env python3
"""Invest Flow web server with Edgar market data and DeepSeek proxy.

Run from the repository root:
    python3 InvestFlowWeb/server.py

The browser app stays lightweight. This process owns 24-hour refresh work and
keeps API keys out of mobile Chrome.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from collectors.market_data_collector import MarketDataCollector
except Exception:  # pragma: no cover - runtime fallback
    MarketDataCollector = None

try:
    from config import CONFIG as EDGAR_CONFIG
except Exception:  # pragma: no cover - runtime fallback
    EDGAR_CONFIG = {}

try:
    from database.client import SupabaseDB
except Exception:  # pragma: no cover - runtime fallback
    SupabaseDB = None

PORT = int(os.getenv("INVEST_FLOW_PORT", "8080"))
REFRESH_SECONDS = int(os.getenv("INVEST_FLOW_MARKET_REFRESH_SECONDS", "900"))

MARKET_CACHE: dict[str, dict] = {
    "updated_at": None,
    "data": {},
    "status": "starting",
}

FALLBACK_MARKET_DATA = {
    "SPY": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
    "QQQ": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
    "KOSPI": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
    "BTC": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
    "ETH": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
}


def collect_market_data() -> dict[str, dict]:
    if not MarketDataCollector:
        return FALLBACK_MARKET_DATA
    collector = MarketDataCollector(EDGAR_CONFIG)
    data = collector.get_all_market_data()
    return data or FALLBACK_MARKET_DATA


def market_loop() -> None:
    while True:
        try:
            MARKET_CACHE["data"] = collect_market_data()
            MARKET_CACHE["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            MARKET_CACHE["status"] = "ok"
        except Exception as exc:
            MARKET_CACHE["status"] = f"error: {exc}"
        time.sleep(REFRESH_SECONDS)


def call_deepseek(messages: list[dict], report_context: str = "") -> str:
    api_key = EDGAR_CONFIG.get("deepseek_api_key") or os.getenv("DEEPSEEK_API_KEY")
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
            self.send_json(MARKET_CACHE)
            return
        if path.path == "/api/health":
            self.send_json({"ok": True, "market": MARKET_CACHE["status"]})
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
            try:
                payload = self.read_json_body()
                answer = call_deepseek(payload.get("messages", []), payload.get("report_context", ""))
                self.send_json({"answer": answer})
            except (urllib.error.URLError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
                self.send_json({"error": str(exc)}, status=502)
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
    threading.Thread(target=market_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), InvestFlowHandler)
    print(f"Invest Flow server: http://0.0.0.0:{PORT}")
    print(f"Market refresh: every {REFRESH_SECONDS}s")
    server.serve_forever()


if __name__ == "__main__":
    main()
