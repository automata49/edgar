from __future__ import annotations

import requests
import yfinance as yf

# symbol → category 역방향 조회용
SYMBOLS: dict[str, dict[str, str]] = {
    "indices":    {"SPX": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "RUSSELL": "^RUT", "KOSPI": "^KS11", "KOSDAQ": "^KQ11"},
    "bonds":      {"US10Y": "^TNX", "US30Y": "^TYX", "TLT": "TLT", "HYG": "HYG"},
    "commodities":{"OIL": "CL=F", "GOLD": "GC=F", "DXY": "DX-Y.NYB"},
    "crypto":     {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "XRP": "XRP-USD"},
    "sector_etf": {
        "SOXX": "SOXX", "SMH": "SMH", "SOXL": "SOXL",
        "XLK": "XLK", "XLF": "XLF", "XLE": "XLE", "XLV": "XLV",
        "XLY": "XLY", "XLP": "XLP", "XLI": "XLI", "XLB": "XLB",
        "XBI": "XBI", "ITB": "ITB", "IYR": "IYR", "VNQ": "VNQ",
        "KRE": "KRE", "XRT": "XRT",
    },
    "style_etf": {
        "SPY": "SPY", "QQQ": "QQQ", "TQQQ": "TQQQ", "DIA": "DIA",
        "IWM": "IWM", "IWF": "IWF", "VUG": "VUG", "RSP": "RSP",
    },
    "theme_etf":  {"LIT": "LIT", "XOP": "XOP", "IGV": "IGV", "EWY": "EWY", "INDA": "INDA", "IBIT": "IBIT"},
    "special":    {"VIX": "^VIX", "SCHD": "SCHD", "VIG": "VIG"},
}

# 빠른 역방향 조회: name → category
CATEGORY_MAP: dict[str, str] = {
    name: cat for cat, syms in SYMBOLS.items() for name in syms
}

_COINGECKO_IDS = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple"}


class MarketCollector:
    """yfinance + CoinGecko 시장 데이터 수집."""

    def __init__(self, config: dict) -> None:
        self.config = config

    def collect(self) -> dict[str, dict]:
        print("📊 시장 데이터 수집 중...")
        result: dict[str, dict] = {}
        total, ok = 0, 0

        for category, syms in SYMBOLS.items():
            for name, ticker in syms.items():
                total += 1
                data = (
                    self._fetch_coingecko(_COINGECKO_IDS[name])
                    if category == "crypto" and name in _COINGECKO_IDS
                    else None
                ) or self._fetch_yahoo(ticker)

                if data:
                    result[name] = data
                    ok += 1

        print(f"✅ 시장 데이터: {ok}/{total}개\n")
        return result

    # ── Private ──────────────────────────────────────────────────────────────

    def _fetch_yahoo(self, symbol: str) -> dict | None:
        try:
            info = yf.Ticker(symbol).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0)
            prev  = info.get("previousClose", price)
            chg   = price - prev
            return {
                "price":          round(price, 2),
                "change":         round(chg, 2),
                "change_percent": round((chg / prev * 100) if prev else 0, 2),
                "previous_close": round(prev, 2),
            }
        except Exception as e:
            print(f"   ⚠️  {symbol}: {str(e)[:50]}")
            return None

    def _fetch_coingecko(self, coin_id: str) -> dict | None:
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"},
                timeout=5,
            )
            d = r.json().get(coin_id, {})
            if d:
                return {"price": round(d["usd"], 2), "change_percent": round(d.get("usd_24h_change", 0), 2)}
        except Exception:
            pass
        return None
