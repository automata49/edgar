from __future__ import annotations

from datetime import datetime


class TelegramReporter:
    """분석 결과를 텔레그램 메시지로 포맷·발송."""

    def __init__(self, bot) -> None:
        self.bot = bot

    async def send(
        self,
        chat_id: int,
        analysis: str,
        stats: dict,
        market_data: dict | None = None,
        youtube_data: list | None = None,
        news_data: list | None = None,
    ) -> None:
        market_data  = market_data or {}
        youtube_data = youtube_data or []
        news_data    = news_data or []

        clean = _strip_markdown(analysis)
        main, action = _split_action(clean)

        await self._send(chat_id, self._header(stats, market_data))
        await self._send(chat_id, main)
        if action:
            await self._send(chat_id, f"📋 액션 플랜:\n\n{action}")
        await self._send(chat_id, self._sources(youtube_data, news_data))

    # ── Format ───────────────────────────────────────────────────────────────

    def _header(self, stats: dict, market_data: dict) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"📊 {now} 트렌드 리포트",
            "━" * 30,
            f"• YouTube: {stats.get('youtube_count', 0)}개",
            f"• 뉴스: {stats.get('website_count', 0)}개",
            "",
        ]
        if market_data:
            lines += self._market_lines(market_data)
        return "\n".join(lines)

    def _market_lines(self, data: dict) -> list[str]:
        def fmt(sym: str, label: str | None = None) -> str:
            d = data.get(sym)
            if not d:
                return ""
            p, pct = d.get("price", 0), d.get("change_percent", 0)
            e = "🔴" if pct < 0 else "🟢"
            return f"{e} {label or sym}: ${p:,.2f} ({pct:+.2f}%)"

        lines = ["━" * 30, "📈 시장 현황", ""]
        for sym in ["SPX", "NASDAQ", "DOW", "KOSPI"]:
            if l := fmt(sym):
                lines.append(l)
        lines.append("")
        if l := fmt("US10Y"):
            lines += ["💰 채권:", l, ""]
        for sym, lbl in [("OIL", "WTI"), ("GOLD", "GOLD"), ("DXY", "DXY")]:
            if l := fmt(sym, lbl):
                lines.append(l)
        lines.append("")
        for sym in ["BTC", "ETH"]:
            if l := fmt(sym):
                lines.append(l)
        lines.append("")
        return lines

    def _sources(self, youtube_data: list, news_data: list) -> str:
        lines = ["📎 출처:"]
        if youtube_data:
            by_cat: dict[str, list] = {}
            for v in youtube_data[:15]:
                by_cat.setdefault(v.get("category", "etc"), []).append(v)
            cat_names = {"market": "시황", "investment": "투자", "realestate": "부동산", "crypto": "크립토"}
            for cat, videos in by_cat.items():
                links = [f"[{v.get('title','')[:25]}...]({v.get('url','')})" for v in videos[:2] if v.get("url")]
                if links:
                    lines.append(f"• {cat_names.get(cat, cat)}: {', '.join(links)}")
        if news_data:
            by_src: dict[str, list] = {}
            for a in news_data[:15]:
                by_src.setdefault(a.get("source", "Unknown"), []).append(a)
            for src, arts in list(by_src.items())[:4]:
                links = [f"[{a.get('title','')[:25]}...]({a.get('url','')})" for a in arts[:2] if a.get("url")]
                if links:
                    lines.append(f"• {src}: {', '.join(links)}")
        return "\n".join(lines)

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _send(self, chat_id: int, text: str) -> None:
        if not text.strip():
            return
        try:
            await self.bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=True)
        except Exception as e:
            print(f"   ⚠️  발송 실패 ({chat_id}): {e}")


# ── Module helpers ────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    for ch in ["#", "*", "_", "`", "~", ">", "|"]:
        text = text.replace(ch, "")
    return text


def _split_action(text: str) -> tuple[str, str | None]:
    if "액션 플랜:" in text:
        a, b = text.split("액션 플랜:", 1)
        return a.strip(), b.strip()
    return text.strip(), None
