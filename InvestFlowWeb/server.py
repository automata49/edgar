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
import urllib.request
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

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
ALLOWED_KINDS = {"income", "expense", "transfer"}
ALLOWED_BUCKETS = {"essential", "discretionary", "investing", "income", "transfer"}


def clean_transaction(item: dict) -> dict:
    kind = item.get("kind") if item.get("kind") in ALLOWED_KINDS else "expense"
    bucket = item.get("bucket") if item.get("bucket") in ALLOWED_BUCKETS else "discretionary"
    return {
        "id": str(item.get("id") or "")[:100],
        "title": str(item.get("title") or "Transaction")[:120],
        "amount": abs(float(item.get("amount") or 0)),
        "kind": kind,
        "bucket": bucket,
        "currency": "USD" if item.get("currency") == "USD" else "KRW",
        "date": str(item.get("date") or "")[:10],
        "institution": str(item.get("institution") or "Manual paste")[:80],
        "raw": str(item.get("raw") or "")[:500],
    }


def call_deepseek_validator(transactions: list[dict], existing: list[dict]) -> dict:
    api_key = os.getenv("DEEPSEEK_API_KEY") or EDGAR_CONFIG.get("deepseek_api_key")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    prompt = f"""Validate Korean/English bank and card transactions for a 50-30-20 budget.
Return JSON only: {{"transactions":[{{"id":"input id","title":"merchant","amount":123,"date":"YYYY-MM-DD","kind":"income|expense|transfer","bucket":"essential|discretionary|investing|income|transfer","reason":"short reason","duplicate":false}}]}}.
Keep every unique input id exactly once. Mark duplicate=true for repeated transactions within input or transactions already present in existing_transactions. A duplicate requires the same real-world transaction (date, amount, merchant/institution and direction); similar recurring purchases on different dates are not duplicates. Correct obvious merchant/date/type/category parsing errors, but never invent a transaction or change a plausible amount. Internal account transfers and card-bill payments are transfer. Income uses income bucket; transfer uses transfer bucket. Housing, utilities, groceries, medical, insurance, transit and necessary education are essential. Lifestyle, dining, shopping, entertainment and travel are discretionary. Savings, debt principal and securities purchases are investing.
INPUT={json.dumps(transactions, ensure_ascii=False)}
EXISTING_TRANSACTIONS={json.dumps(existing, ensure_ascii=False)}"""
    request_body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise financial transaction validator. Produce JSON only."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "temperature": 0,
        "max_tokens": 12000,
    }).encode("utf-8")
    request = urllib.request.Request(
        DEEPSEEK_URL,
        data=request_body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=50) as remote_response:
        payload = json.loads(remote_response.read().decode("utf-8"))
    content = payload.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    return {"model": model, "result": json.loads(content)}


def normalize_deepseek_result(originals: list[dict], result: dict) -> list[dict]:
    by_id = {item["id"]: item for item in originals}
    seen_ids: set[str] = set()
    verified = []
    for proposed in result.get("transactions", []) if isinstance(result, dict) else []:
        original = by_id.get(str(proposed.get("id") or ""))
        if not original or original["id"] in seen_ids or proposed.get("duplicate") is True:
            continue
        kind = proposed.get("kind") if proposed.get("kind") in ALLOWED_KINDS else original["kind"]
        bucket = proposed.get("bucket") if proposed.get("bucket") in ALLOWED_BUCKETS else original["bucket"]
        if kind == "income":
            bucket = "income"
        elif kind == "transfer":
            bucket = "transfer"
        elif bucket in {"income", "transfer"}:
            bucket = "discretionary"
        try:
            amount = abs(float(proposed.get("amount") or 0)) or original["amount"]
        except (TypeError, ValueError):
            amount = original["amount"]
        date = str(proposed.get("date") or "")
        if len(date) != 10 or date[4:5] != "-" or date[7:8] != "-":
            date = original["date"]
        verified.append({
            **original,
            "title": str(proposed.get("title") or original["title"]).strip()[:120] or original["title"],
            "amount": amount,
            "date": date,
            "kind": kind,
            "bucket": bucket,
            "reason": str(proposed.get("reason") or "DeepSeek verified")[:180],
            "included": kind != "transfer",
        })
        seen_ids.add(original["id"])
    return verified


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
            try:
                payload = self.read_json_body()
                transactions = [clean_transaction(item) for item in (payload.get("transactions") or [])[:150]]
                transactions = [item for item in transactions if item["id"] and item["amount"] > 0]
                existing = [clean_transaction(item) for item in (payload.get("existing_transactions") or [])[:500]]
                if not transactions:
                    self.send_json({"error": "No valid transactions"}, status=400)
                    return
                deepseek = call_deepseek_validator(transactions, existing)
                verified = normalize_deepseek_result(transactions, deepseek["result"])
                self.send_json({
                    "status": "ok",
                    "model": deepseek["model"],
                    "transactions": verified,
                    "duplicates_removed": len(transactions) - len(verified),
                })
            except Exception as exc:
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
    server = ThreadingHTTPServer(("0.0.0.0", PORT), InvestFlowHandler)
    print(f"Invest Flow server: http://0.0.0.0:{PORT}")
    print("Mode: lightweight static + Supabase state")
    server.serve_forever()


if __name__ == "__main__":
    main()
