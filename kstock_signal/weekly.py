"""Weekly 리포트: 지난 7일 수집 데이터(시장·뉴스·리서치·Daily 리포트) → 요약 + AI 해설.

주간 등락률·건수 같은 집계는 저장된 값으로 코드가 계산하고,
AI(ModelRouter `weekly_review`)는 그 집계만 보고 해설을 씁니다. 숫자를 새로 만들지 않도록 지시합니다.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from kstock_signal.reporters.research_text import (
    CHANGE_MARK,
    group_by_stock,
    one_line,
    opinion_target,
    won,
)

KEY_SYMBOLS = ["SPX", "NASDAQ", "DOW", "KOSPI", "KOSDAQ", "US10Y", "DXY", "OIL", "GOLD", "BTC", "ETH", "VIX"]
KST = timezone(timedelta(hours=9))

WEEKLY_SYSTEM = """너는 개인 투자자의 주간 리뷰를 돕는 애널리스트다. 한국어로 답한다.
- 제공된 JSON의 숫자만 인용한다. 새로 계산하거나 추정한 숫자를 쓰지 않는다.
- Markdown 기호(#, *, _, `)를 쓰지 않는다. 이모지와 일반 텍스트만 쓴다.
- 매수·매도 지시를 하지 않는다. 확인할 점과 반증 조건을 제시한다.
- 아래 4개 제목으로 1500자 이내:
🧭 이번 주 한눈에 (3줄)
📈 시장 흐름
📑 리서치 흐름 (목표가 상향·하향이 몰린 종목과 공통 주제)
🔭 다음 주 체크포인트 (3~5개)"""


def market_changes(rows: list[dict]) -> dict[str, dict]:
    """market_data 행(시간순) → 심볼별 {first, last, change_pct} (주초 대비 주말 가격)."""
    first: dict[str, float] = {}
    last: dict[str, float] = {}
    category: dict[str, str] = {}
    for r in rows:
        sym, price = r.get("symbol"), r.get("price")
        if sym is None or price in (None, 0):
            continue
        first.setdefault(sym, float(price))
        last[sym] = float(price)
        category[sym] = r.get("category") or ""
    out = {}
    for sym, p0 in first.items():
        p1 = last[sym]
        out[sym] = {"first": p0, "last": p1, "change_pct": round((p1 / p0 - 1) * 100, 2) if p0 else None,
                    "category": category[sym]}
    return out


def research_stats(rows: list[dict]) -> dict:
    groups = group_by_stock(rows)
    stocks = []
    for label, items in groups.items():
        targets = [r["target_value"] for r in items if r.get("target_value")]
        changes = Counter(r.get("target_change") for r in items)
        stocks.append({
            "stock": label, "reports": len(items),
            "firms": sorted({str(r.get("firm")) for r in items}),
            "target_min": min(targets) if targets else None, "target_max": max(targets) if targets else None,
            "target_up": changes.get("상향", 0), "target_down": changes.get("하향", 0),
            "sentiment": Counter(r.get("sentiment") for r in items).most_common(1)[0][0],
            "latest": one_line(items[0]), "opinion": opinion_target(items[0]),
        })
    stocks.sort(key=lambda x: (x["reports"], x["target_up"]), reverse=True)
    return {
        "total": len(rows), "stocks": len(groups),
        "target_up": sum(s["target_up"] for s in stocks), "target_down": sum(s["target_down"] for s in stocks),
        "sentiment": dict(Counter(r.get("sentiment") or "중립" for r in rows)),
        "top": stocks,
    }


def _fmt_price(v: float) -> str:
    return f"{v:,.2f}" if v < 1000 else f"{v:,.0f}"


class WeeklyReport:
    def __init__(self, config: dict, router, db) -> None:
        self.config = config
        self.router = router
        self.db = db

    def build(self, now: datetime | None = None) -> dict | None:
        """집계 + AI 해설 → {'text', 'model', 'stats'}. DB가 없으면 None."""
        if self.db is None:
            return None
        now = now or datetime.now(timezone.utc)
        since = (now - timedelta(days=7)).isoformat()
        market = market_changes(self.db.market_since(since))
        research = self.db.research_since(since)
        news = self.db.news_since(since)
        dailies = self.db.reports_since(since, "daily")
        rstats = research_stats(research)

        data = {
            "기간": f"{(now - timedelta(days=7)).astimezone(KST):%m/%d} ~ {now.astimezone(KST):%m/%d}",
            "시장_주간등락률": {s: market[s]["change_pct"] for s in KEY_SYMBOLS if s in market},
            "섹터ETF_주간등락률": {s: m["change_pct"] for s, m in market.items() if m["category"] == "sector_etf"},
            "리서치": {k: rstats[k] for k in ("total", "stocks", "target_up", "target_down", "sentiment")},
            "리서치_상위종목": [{k: s[k] for k in ("stock", "reports", "firms", "opinion", "target_up",
                                                 "target_down", "latest")} for s in rstats["top"][:12]],
            "뉴스_건수": len(news),
            "뉴스_주요제목": [n.get("title") for n in news[:15]],
            "Daily_액션플랜": [str(d.get("action_plan") or "")[:300] for d in dailies[-5:]],
        }
        result = self.router.run("weekly_review", json.dumps(data, ensure_ascii=False), system=WEEKLY_SYSTEM)
        text = self.format(data["기간"], market, rstats, news, result.text, result.model if result.ok else None)
        return {"text": text, "model": result.model if result.ok else None, "stats": data}

    @staticmethod
    def format(period: str, market: dict, rstats: dict, news: list[dict], commentary: str,
               model: str | None) -> str:
        lines = [f"🗓 Weekly 리포트 ({period})", "━" * 30, "📈 주간 시장 (주초 → 주말)"]
        for sym in KEY_SYMBOLS:
            m = market.get(sym)
            if m and m["change_pct"] is not None:
                e = "🟢" if m["change_pct"] > 0 else "🔴" if m["change_pct"] < 0 else "⚪"
                lines.append(f"{e} {sym}: {_fmt_price(m['last'])} ({m['change_pct']:+.2f}%)")
        sectors = sorted(((s, m) for s, m in market.items() if m["category"] == "sector_etf"
                          and m["change_pct"] is not None), key=lambda x: x[1]["change_pct"], reverse=True)

        def fmt(items):
            return ", ".join(f"{s} {m['change_pct']:+.1f}%" for s, m in items)
        if len(sectors) >= 6:
            lines += [f"섹터 강세: {fmt(sectors[:3])}", f"섹터 약세: {fmt(sectors[-3:][::-1])}"]
        elif sectors:
            lines.append(f"섹터: {fmt(sectors)}")
        if len(lines) == 3:
            lines.append("저장된 시장 데이터가 없습니다.")

        lines += ["", "━" * 30,
                  (f"📑 증권사 리포트 {rstats['total']}건 · {rstats['stocks']}종목 · "
                   f"목표가 상향 {rstats['target_up']} · 하향 {rstats['target_down']}")]
        for s in rstats["top"][:10]:
            rng = ""
            if s["target_min"]:
                rng = f" · 목표 {won(s['target_min'])}" if s["target_min"] == s["target_max"] \
                    else f" · 목표 {won(s['target_min'])}~{won(s['target_max'])}"
            moves = "".join([CHANGE_MARK["상향"] * s["target_up"], CHANGE_MARK["하향"] * s["target_down"]])
            lines.append(f"• {s['stock']} {s['reports']}건{rng} {moves}".rstrip())
            lines.append(f"  └ {s['latest']}")
        if not rstats["top"]:
            lines.append("이번 주 저장된 리포트가 없습니다.")

        lines += ["", "━" * 30, f"📰 뉴스 {len(news)}건"]
        for src, n in Counter(a.get("source") or "기타" for a in news).most_common(5):
            lines.append(f"• {src}: {n}건")

        lines += ["", "━" * 30, "🤖 AI 주간 해설" + (f" ({model})" if model else ""), commentary]
        return "\n".join(lines)
