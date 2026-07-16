from __future__ import annotations

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from collectors.market_data_collector import MarketDataCollector
except Exception:
    MarketDataCollector = None


FALLBACK_MARKET_DATA = {
    "SPY": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
    "QQQ": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
    "KOSPI": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
    "BTC": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
    "ETH": {"price": 0, "change": 0, "change_percent": 0, "previous_close": 0},
}


def market_data() -> dict:
    if not MarketDataCollector:
        return FALLBACK_MARKET_DATA
    config = {
        "alpha_vantage_api_key": os.getenv("ALPHA_VANTAGE_API_KEY"),
        "finnhub_api_key": os.getenv("FINNHUB_API_KEY"),
    }
    return MarketDataCollector(config).get_all_market_data() or FALLBACK_MARKET_DATA


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_json({
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data": market_data(),
            "status": "ok",
        })

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
