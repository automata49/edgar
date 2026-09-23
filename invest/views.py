"""텔레그램 조회 화면(메뉴·카드) 포맷터.

텔레그램 객체에 의존하지 않는 순수 함수라 테스트하기 쉽습니다.
각 함수는 Page(text=HTML, buttons=[[(라벨, callback_data)]])를 돌려주고,
핸들러(telegram_bot/handlers/browse.py)가 이를 메시지와 인라인 버튼으로 바꿉니다.
숫자는 시트·DB·Pepper 값을 그대로 보여주고 새로 계산하지 않습니다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import escape

from invest import pepper_results

PER_PAGE = 8
_LIMIT = 3900        # 텔레그램 4096자 제한 여유

VERDICT = {"PASS": "✅", "FAIL": "❌", "UNKNOWN": "⚪"}
MARKET_CATEGORIES = {
    "indices": "📈 지수", "bonds": "🏦 채권", "commodities": "🛢 원자재·달러", "crypto": "🪙 코인",
    "sector_etf": "🏭 섹터 ETF", "style_etf": "🎯 스타일 ETF", "theme_etf": "🧭 테마 ETF", "special": "✨ 기타",
}


@dataclass
class Page:
    text: str
    buttons: list[list[tuple[str, str]]] = field(default_factory=list)


# ── 값 포맷 ───────────────────────────────────────────────────
def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def num(v, digits: int = 2) -> str:
    if not _is_num(v):
        return escape(str(v)) if v not in (None, "") else "-"
    if float(v).is_integer():
        return f"{int(v):,}"
    return f"{v:,.{digits}f}".rstrip("0").rstrip(".")


def won(v) -> str:
    return f"{v:,.0f}원" if _is_num(v) else "-"


def signed_won(v) -> str:
    return f"{v:+,.0f}원" if _is_num(v) else "-"


def pct(v, digits: int = 1) -> str:
    return f"{v * 100:.{digits}f}%" if _is_num(v) else "-"


def price(v, currency: str | None) -> str:
    if not _is_num(v):
        return "-"
    return won(v) if currency == "KRW" else f"{num(v)} {escape(currency or '')}".strip()


def _cut(text: str) -> str:
    # 줄 단위로 자릅니다. 각 줄의 HTML 태그는 그 줄 안에서 닫히므로 태그가 깨지지 않습니다.
    return text if len(text) <= _LIMIT else text[:_LIMIT].rsplit("\n", 1)[0] + "\n…(생략)"


def _grid(items: list[tuple[str, str]], per_row: int = 3) -> list[list[tuple[str, str]]]:
    return [items[i:i + per_row] for i in range(0, len(items), per_row)]


def _nav(back: str = "home", refresh: str | None = None) -> list[tuple[str, str]]:
    row = [("⬅️ 뒤로", f"v:{back}")] if back != "home" else []
    if refresh:
        row.append(("🔄 새로고침", f"v:{refresh}:r"))
    row.append(("🏠 메뉴", "v:home"))
    return row


def _pager(prefix: str, page: int, total: int) -> list[list[tuple[str, str]]]:
    """페이지가 2개 이상일 때만 [이전 · n/N · 다음] 줄을 돌려줍니다."""
    pages = max(1, -(-total // PER_PAGE))
    if pages == 1:
        return []
    row = []
    if page > 1:
        row.append(("◀ 이전", f"v:{prefix}:{page - 1}"))
    row.append((f"{page}/{pages}", "v:noop"))
    if page < pages:
        row.append(("다음 ▶", f"v:{prefix}:{page + 1}"))
    return [row]


def _tickers(rows: list[dict]) -> list[str]:
    seen: list[str] = []
    for r in rows:
        t = str(r.get("Ticker") or "").strip()
        if t and t not in seen:
            seen.append(t)
    return seen


def _sheet_header(title: str, sheet: dict) -> str:
    s = sheet.get("settings", {})
    lines = [f"<b>{title}</b>"]
    meta = [f"기준일 {escape(str(s.get('평가 기준일') or '-'))}", f"출처 {escape(sheet.get('source', '-'))}"]
    lines.append("<i>" + " · ".join(meta) + "</i>")
    if str(s.get("데이터 모드", "")).lower() == "demo":
        lines.append("🧪 Demo 모드 — 가상 예시 데이터입니다")
    return "\n".join(lines)


def _status(r: dict) -> str:
    st = r.get("입력 상태")
    return "" if st in (None, "", "OK") else f" · ⚠️ {escape(str(st))}"


# ── 메뉴 ─────────────────────────────────────────────────────
def home(sheet_url: str | None = None) -> Page:
    text = ("🗂 <b>Edgar 데이터 보기</b>\n"
            "보고 싶은 항목을 누르세요. 채팅으로 \"포트폴리오 보여줘\", \"뉴스 확인\"처럼 말해도 됩니다.\n\n"
            "<b>📒 Google 시트 (Pepper)</b>\n포트폴리오 · 리서치 · 재무 · 밸류에이션 · 가격\n\n"
            "<b>📡 수집 데이터</b>\n증권사 리포트 · 시장 · 뉴스 · YouTube · Daily/Weekly 리포트 · Pepper 점수")
    buttons = [
        [("💼 포트폴리오", "v:pf"), ("🔎 리서치 판정", "v:rs")],
        [("💵 재무", "v:fin"), ("📐 밸류에이션", "v:val"), ("💹 가격", "v:px")],
        [("📈 시장", "v:mkt"), ("📰 뉴스", "v:news:1"), ("🎬 YouTube", "v:yt:1")],
        [("📑 증권사 리포트", "v:rr"), ("🧮 Pepper 점수", "v:pep")],
        [("📝 Daily 리포트", "v:rpt"), ("🗓 Weekly 리포트", "v:wk")],
    ]
    if sheet_url:
        buttons.append([("📎 시트 열기", "url:" + sheet_url)])
    return Page(text, buttons)


def unavailable(what: str, hint: str) -> Page:
    return Page(f"⚠️ <b>{escape(what)}</b>을(를) 불러올 수 없습니다.\n{escape(hint)}", [_nav()])


# ── Google 시트 ──────────────────────────────────────────────
def portfolio(sheet: dict) -> Page:
    rows = sheet["tables"].get("Portfolio", [])
    s = sheet.get("settings", {})
    lines = [_sheet_header("💼 포트폴리오", sheet)]
    lines.append(f"현금 {won(s.get('현금 KRW'))} · ${num(s.get('현금 USD'))} · USD/KRW {num(s.get('USD/KRW'))}")
    lines.append(f"한도: 종목 비중 {pct(s.get('종목 비중 한도'))} · 가격 위험 {pct(s.get('가격 위험 한도'))}")
    if not rows:
        lines.append("\n보유·계획 종목이 없습니다.")
    for r in rows:
        t = escape(str(r.get("Ticker")))
        cur, plan, delta = r.get("현재 수량"), r.get("적용 계획수량", r.get("계획 수량")), r.get("증감 수량")
        delta_txt = f" ({delta:+,g})" if _is_num(delta) and delta else ""
        check = r.get("점검")
        lines += [
            "",
            f"<b>{t}</b> · {escape(str(r.get('전략') or '-'))} · {escape(str(r.get('섹터') or '-'))}{_status(r)}",
            f"  수량 {num(cur)} → 계획 {num(plan)}{delta_txt}",
            f"  평가 {won(r.get('평가액 KRW'))} · 비중 {pct(r.get('현재 비중'))} → {pct(r.get('계획 비중'))}",
            f"  손익 {signed_won(r.get('가격손익 KRW'))} · 손절 {price(r.get('손절 기준'), r.get('통화'))}"
            + (f" · 🔔 {escape(str(check))}" if check else ""),
        ]
    buttons = _grid([(f"🔍 {t}", f"v:pf:{t}") for t in _tickers(rows)])
    buttons.append(_nav(refresh="pf"))
    return Page(_cut("\n".join(lines)), buttons)


def portfolio_detail(sheet: dict, ticker: str) -> Page:
    rows = [r for r in sheet["tables"].get("Portfolio", []) if str(r.get("Ticker")).upper() == ticker.upper()]
    if not rows:
        return Page(f"{escape(ticker)}은(는) 포트폴리오 탭에 없습니다.", [_nav("pf")])
    r = rows[0]
    cur = r.get("통화")
    lines = [
        f"💼 <b>{escape(ticker)}</b> · {escape(str(r.get('전략') or '-'))} · {escape(str(r.get('섹터') or '-'))}{_status(r)}",
        "",
        "<b>보유</b>",
        f"• 수량 {num(r.get('현재 수량'))} → 계획 {num(r.get('적용 계획수량', r.get('계획 수량')))}",
        f"• 평균단가 {price(r.get('평균단가'), cur)} · 현재가 {price(r.get('현재가'), cur)}",
        f"• 평가액 {won(r.get('평가액 KRW'))} → 계획 {won(r.get('계획 평가액 KRW'))}",
        f"• 비중 {pct(r.get('현재 비중'))} → {pct(r.get('계획 비중'))} (종목 합산 {pct(r.get('종목 합산비중'))})",
        f"• 가격손익 {signed_won(r.get('가격손익 KRW'))}",
        f"• 예상 거래액 {won(r.get('예상 거래액 KRW'))}",
        "",
        "<b>위험</b>",
        f"• 손절 기준 {price(r.get('손절 기준'), cur)}",
        f"• 가격위험 {won(r.get('현재 가격위험 KRW'))} → 계획 {won(r.get('계획 가격위험 KRW'))}",
        f"• 스트레스 손실 {won(r.get('스트레스 손실 KRW'))}",
        "",
        "<b>논리</b>",
        f"• 보유 논리: {escape(str(r.get('보유 논리') or '-'))}",
        f"• 무효화 조건: {escape(str(r.get('무효화 조건') or '-'))}",
        f"• 점검: {escape(str(r.get('점검') or '-'))} · 검토일 {escape(str(r.get('검토일') or '-'))}",
    ]
    buttons = [[("🔎 리서치", f"v:rs:{ticker}"), ("💵 재무", f"v:fin:{ticker}"), ("🧮 점수", f"v:pep:{ticker}")],
               _nav("pf")]
    return Page(_cut("\n".join(lines)), buttons)


def research(sheet: dict) -> Page:
    rows = sheet["tables"].get("Research", [])
    lines = [_sheet_header("🔎 리서치 판정", sheet), ""]
    if not rows:
        lines.append("리서치 항목이 없습니다.")
    for t in _tickers(rows):
        items = [r for r in rows if str(r.get("Ticker")) == t]
        counts = {k: sum(1 for r in items if r.get("판정") == k) for k in VERDICT}
        strategies = ", ".join(sorted({str(r.get("전략")) for r in items if r.get("전략")}))
        lines.append(f"<b>{escape(t)}</b> ({escape(strategies)}) — "
                     + " ".join(f"{VERDICT[k]}{n}" for k, n in counts.items() if n))
    lines.append("\n✅ 통과 · ❌ 실패 · ⚪ 미확인")
    buttons = _grid([(f"🔍 {t}", f"v:rs:{t}") for t in _tickers(rows)])
    buttons.append(_nav(refresh="rs"))
    return Page(_cut("\n".join(lines)), buttons)


def research_detail(sheet: dict, ticker: str) -> Page:
    rows = [r for r in sheet["tables"].get("Research", []) if str(r.get("Ticker")).upper() == ticker.upper()]
    if not rows:
        return Page(f"{escape(ticker)}의 리서치 항목이 없습니다.", [_nav("rs")])
    lines = [f"🔎 <b>{escape(ticker)} 리서치</b>"]
    for strategy in sorted({str(r.get("전략") or "-") for r in rows}):
        lines += ["", f"<b>[{escape(strategy)}]</b>"]
        for r in (x for x in rows if str(x.get("전략") or "-") == strategy):
            obs = " ".join(str(v) for v in (r.get("관측값"), r.get("단위")) if v not in (None, ""))
            line = f"{VERDICT.get(r.get('판정'), '•')} {escape(str(r.get('평가 항목')))}"
            if obs:
                line += f": {escape(obs)}"
            if r.get("근거 상태") and r.get("근거 상태") != "확인":
                line += f" <i>({escape(str(r.get('근거 상태')))})</i>"
            lines.append(line)
            if r.get("판정") != "UNKNOWN" and r.get("평가 근거"):
                lines.append(f"   └ {escape(str(r['평가 근거']))}")
    buttons = [[("💼 포트폴리오", f"v:pf:{ticker}"), ("💵 재무", f"v:fin:{ticker}")], _nav("rs")]
    return Page(_cut("\n".join(lines)), buttons)


def financials(sheet: dict, ticker: str | None = None) -> Page:
    rows = sheet["tables"].get("Financials", [])
    if ticker:
        rows = [r for r in rows if str(r.get("Ticker")).upper() == ticker.upper()]
    lines = [_sheet_header("💵 재무 (TTM)" + (f" · {escape(ticker)}" if ticker else ""), sheet)]
    if not rows:
        lines.append("\n재무 입력이 없습니다.")
    for r in rows:
        cur = r.get("통화")
        lines += [
            "",
            (f"<b>{escape(str(r.get('Ticker')))}</b> · {escape(str(r.get('기간 역할') or '-'))} · "
             f"TTM {escape(str(r.get('TTM 종료일') or '-'))}{_status(r)}"),
            (f"  ROE {pct(r.get('ROE'))} = 순이익률 {pct(r.get('순이익률'))} × 회전율 {num(r.get('자산회전율'))} "
             f"× 레버리지 {num(r.get('재무레버리지'))}"),
            f"  매출 {price(r.get('매출'), cur)} · 순이익 {price(r.get('순이익'), cur)}",
            f"  FCF {price(r.get('FCF'), cur)} · 현금전환율 {pct(r.get('현금 전환율'), 0)} · EPS {num(r.get('TTM EPS'))}",
        ]
    buttons = [] if ticker else _grid([(f"🔍 {t}", f"v:fin:{t}") for t in _tickers(rows)])
    buttons.append(_nav("fin" if ticker else "home", refresh=None if ticker else "fin"))
    return Page(_cut("\n".join(lines)), buttons)


def valuation(sheet: dict) -> Page:
    rows = sheet["tables"].get("Valuation", [])
    lines = [_sheet_header("📐 밸류에이션 가정", sheet)]
    if not rows:
        lines.append("\n밸류에이션 입력이 없습니다.")
    for r in rows:
        lines += [
            "",
            f"<b>{escape(str(r.get('Ticker')))}</b> · {num(r.get('기간 년'))}년 · 검토 {escape(str(r.get('검토일') or '-'))}{_status(r)}",
            f"  가정: EPS 성장 {pct(r.get('EPS 성장 가정'))} · 말기 PER {num(r.get('말기 PER'))} · 요구수익률 {pct(r.get('요구수익률'))}",
            f"  현재가 {num(r.get('현재가'))} → 말기 가격 {num(r.get('말기 가격'))}",
            (f"  연환산 수익률 {pct(r.get('연환산 가격수익률'))} · 필요 EPS CAGR {pct(r.get('요구 EPS CAGR'))} "
             f"· 여유 {pct(r.get('가정 성장 여유'))}"),
            f"  <i>{escape(str(r.get('가정 근거') or ''))}</i>",
        ]
    return Page(_cut("\n".join(lines)), [_nav(refresh="val")])


def prices(sheet: dict) -> Page:
    rows = sheet["tables"].get("Prices", [])
    lines = [_sheet_header("💹 가격", sheet), ""]
    if not rows:
        lines.append("가격 입력이 없습니다.")
    for r in rows:
        lines.append(f"<b>{escape(str(r.get('Ticker')))}</b> {escape(str(r.get('종목명') or ''))} · "
                     f"{price(r.get('현재가'), r.get('통화'))} ({escape(str(r.get('가격일') or '-'))})"
                     f" · {escape(str(r.get('시장') or ''))}{_status(r)}")
    return Page(_cut("\n".join(lines)), [_nav(refresh="px")])


# ── 수집 데이터 ──────────────────────────────────────────────
def market(snapshot: dict, category_map: dict[str, str], created_at: str | None, category: str | None = None) -> Page:
    groups: dict[str, list[tuple[str, dict]]] = {}
    for sym, d in (snapshot or {}).items():
        groups.setdefault(category_map.get(sym, "special"), []).append((sym, d or {}))
    when = f"<i>수집 {escape(str(created_at or '-')[:16].replace('T', ' '))}</i>"
    if not groups:
        return Page("📈 <b>시장</b>\n저장된 시장 데이터가 없습니다. /monitor 로 수집하세요.", [_nav()])
    order = [c for c in MARKET_CATEGORIES if c in groups] + [c for c in groups if c not in MARKET_CATEGORIES]
    shown = [category] if category in groups else order[:3]
    lines = ["📈 <b>시장</b>", when]
    for c in shown:
        lines += ["", f"<b>{MARKET_CATEGORIES.get(c, c)}</b>"]
        for sym, d in groups[c]:
            chg = d.get("change_percent", d.get("change_pct"))
            arrow = "🔺" if _is_num(chg) and chg > 0 else "🔻" if _is_num(chg) and chg < 0 else "▫️"
            chg_txt = f"{chg:+.2f}%" if _is_num(chg) else "-"
            lines.append(f"{arrow} <code>{escape(sym):<8}</code> {num(d.get('price'))}  {chg_txt}")
    buttons = _grid([(MARKET_CATEGORIES.get(c, c), f"v:mkt:{c}") for c in order], per_row=2)
    buttons.append(_nav("mkt" if category else "home"))
    return Page(_cut("\n".join(lines)), buttons)


def _date(v) -> str:
    return escape(str(v or "")[:10])


def news(articles: list[dict], page: int = 1) -> Page:
    total = len(articles)
    chunk = articles[(page - 1) * PER_PAGE: page * PER_PAGE]
    lines = [f"📰 <b>최근 뉴스</b> ({total}건)"]
    if not chunk:
        lines.append("저장된 뉴스가 없습니다.")
    for i, a in enumerate(chunk, (page - 1) * PER_PAGE + 1):
        title = escape(str(a.get("title") or "(제목 없음)"))
        url = a.get("url")
        link = f'<a href="{escape(url, quote=True)}">{title}</a>' if url else title
        lines.append(f"\n{i}. {link}\n   <i>{escape(str(a.get('source') or ''))} · "
                     f"{_date(a.get('published_at') or a.get('collected_at'))}</i>")
    return Page(_cut("\n".join(lines)), [*_pager("news", page, total), _nav()])


def videos(items: list[dict], page: int = 1) -> Page:
    total = len(items)
    chunk = items[(page - 1) * PER_PAGE: page * PER_PAGE]
    lines = [f"🎬 <b>최근 YouTube</b> ({total}개)"]
    if not chunk:
        lines.append("저장된 영상이 없습니다.")
    for i, v in enumerate(chunk, (page - 1) * PER_PAGE + 1):
        title = escape(str(v.get("title") or "(제목 없음)"))
        url = v.get("url")
        link = f'<a href="{escape(url, quote=True)}">{title}</a>' if url else title
        lines.append(f"\n{i}. {link}\n   <i>{escape(str(v.get('channel') or ''))} · "
                     f"{escape(str(v.get('category') or ''))} · {_date(v.get('published_at') or v.get('collected_at'))}</i>")
    return Page(_cut("\n".join(lines)), [*_pager("yt", page, total), _nav()])


def report(rep: dict | None, fallback_text: str | None = None) -> Page:
    if rep:
        lines = [f"📝 <b>최근 리포트</b> #{escape(str(rep.get('id', '')))}",
                 (f"<i>{escape(str(rep.get('created_at') or '')[:16].replace('T', ' '))} · "
                  f"YouTube {rep.get('youtube_count', 0)} · 뉴스 {rep.get('website_count', 0)}</i>"), "",
                 escape(str(rep.get("analysis") or ""))]
        if rep.get("action_plan"):
            lines += ["", "<b>🎯 액션 플랜</b>", escape(str(rep["action_plan"]))]
        return Page(_cut("\n".join(lines)), [[("📈 시장 스냅샷", "v:mkt")], _nav()])
    if fallback_text:
        return Page(_cut("📝 <b>최근 리포트</b>\n\n" + escape(fallback_text)), [_nav()])
    return Page("📝 저장된 리포트가 없습니다. /monitor 로 먼저 실행하세요.", [_nav()])


def pepper(results: dict | None) -> Page:
    if not results:
        return unavailable("Pepper 점수", "pepper score 를 먼저 실행하세요.")
    lines = pepper_results.summary_lines(results)
    text = f"<b>{escape(lines[0])}</b>\n\n" + "\n".join(escape(x) for x in lines[1:])
    tickers = list(results.get("tickers", {}))
    buttons = _grid([(f"🔍 {t}", f"v:pep:{t}") for t in tickers[:24]], per_row=2)
    buttons.append(_nav())
    return Page(_cut(text), buttons)


def pepper_detail(results: dict | None, ticker: str) -> Page:
    r = (results or {}).get("tickers", {}).get(ticker)
    if not r:
        return Page(f"{escape(ticker)}의 Pepper 결과가 없습니다.", [_nav("pep")])
    text = escape(pepper_results.ticker_card(ticker, r)) + f"\n\n<i>기준일 {escape(str(results.get('asof')))}</i>"
    return Page(_cut(text), [[("🤖 AI 해석 (Astra)", f"v:ai:{ticker}")], _nav("pep")])


# ── 증권사 리서치 리포트 ─────────────────────────────────────
_MARK = {"상향": "▲", "하향": "▼", "신규": "🆕"}
_SENT = {"긍정": "🟢", "중립": "⚪", "부정": "🔴"}


def _target(v, change) -> str:
    return f"목표 {won(v)}{_MARK.get(change, '')}" if _is_num(v) and v else ""


def _stock_key(row: dict) -> str:
    """callback_data(64바이트)에 넣을 종목 키: 코드 우선, 없으면 이름 앞 15자."""
    return str(row.get("stock_code") or str(row.get("stock_name") or "")[:15])


def research_stocks(stocks: list[dict]) -> Page:
    """stock_research 뷰 행 → 종목별 목록."""
    lines = [f"📑 <b>증권사 리포트 · 종목별</b> ({len(stocks)}종목)", "<i>최근 리포트 순 · 네이버 종목분석</i>"]
    if not stocks:
        lines.append("\n저장된 리포트가 없습니다. 매일 Daily 실행 때 수집됩니다.")
    for r in stocks[:25]:
        code = f" ({escape(str(r['stock_code']))})" if r.get("stock_code") else ""
        opinion = r.get("last_opinion") if r.get("last_opinion") not in (None, "미확인") else ""
        meta = " · ".join(x for x in (escape(str(opinion or "")), _target(r.get("last_target"), r.get("last_target_change"))) if x)
        lines += [
            "",
            (f"{_SENT.get(r.get('last_sentiment'), '•')} <b>{escape(str(r.get('stock_name')))}</b>{code} "
             f"· {r.get('report_count', 0)}건 (30일 {r.get('reports_30d', 0)})"),
            f"  {_date(r.get('last_report_day'))} {escape(str(r.get('last_firm') or ''))}" + (f" · {meta}" if meta else ""),
            f"  └ {escape(str(r.get('last_one_line') or ''))}",
        ]
    buttons = _grid([(f"🔍 {str(r.get('stock_name'))[:10]}", f"v:rr:{_stock_key(r)}") for r in stocks[:24]], per_row=3)
    buttons.append(_nav())
    return Page(_cut("\n".join(lines)), buttons)


def research_reports(rows: list[dict], query: str) -> Page:
    """한 종목의 최근 리포트 카드."""
    if not rows:
        return Page(f"📑 '{escape(query)}' 리포트가 없습니다.", [_nav("rr")])
    first = rows[0]
    code = f" ({escape(str(first['stock_code']))})" if first.get("stock_code") else ""
    lines = [f"📑 <b>{escape(str(first.get('stock_name')))}</b>{code} · 최근 리포트 {len(rows)}건"]
    for r in rows:
        s = r.get("summary") or {}
        opinion = str(r.get("opinion") or "미확인")
        if s.get("opinion_change") not in (None, "", "미확인"):
            opinion += f"({s['opinion_change']})"
        meta = " · ".join(x for x in (escape(opinion), _target(r.get("target_value"), r.get("target_change")),
                                      f"{_SENT.get(r.get('sentiment'), '')}{escape(str(r.get('sentiment') or ''))}") if x)
        lines += ["", f"<b>{_date(r.get('report_day'))} {escape(str(r.get('firm') or ''))}</b> — {escape(str(r.get('title') or ''))}",
                  meta]
        if s.get("one_line"):
            lines.append(f"<i>{escape(str(s['one_line']))}</i>")
        lines += [f"• {escape(str(p))}" for p in (s.get("key_points") or [])[:3]]
        lines += [f"⚠️ {escape(str(p))}" for p in (s.get("risks") or [])[:2]]
        nums = " · ".join(f"{n.get('label')} {n.get('value')}" for n in (s.get("numbers") or [])[:4])
        if nums:
            lines.append(f"📊 {escape(nums)}")
        if r.get("pdf_url"):
            lines.append(f'<a href="{escape(str(r["pdf_url"]), quote=True)}">📄 PDF</a>')
    return Page(_cut("\n".join(lines)), [_nav("rr")])


def weekly(rep: dict | None) -> Page:
    if not rep:
        return Page("🗓 저장된 Weekly 리포트가 없습니다. /weekly 로 지금 만들 수 있습니다.", [_nav()])
    text = f"<i>{escape(str(rep.get('created_at') or '')[:16].replace('T', ' '))}</i>\n" + escape(str(rep.get("analysis") or ""))
    return Page(_cut(text), [_nav()])


# ── 자연어 → 화면 ─────────────────────────────────────────────
_SHOW = re.compile(r"보여|확인|알려|조회|봐|볼래|열어|정리|현황|목록|메뉴")
_INTENTS = [
    (re.compile(r"메뉴|데이터\s*보기|시트\s*(메뉴|목록)"), "home"),
    (re.compile(r"증권사|리서치\s*리포트|애널리스트|목표\s*주가"), "rr"),
    (re.compile(r"주간|위클리|weekly", re.IGNORECASE), "wk"),
    (re.compile(r"포트폴리오|보유\s*종목|내\s*종목|잔고"), "pf"),
    (re.compile(r"리서치|판정"), "rs"),
    (re.compile(r"재무|ROE|듀퐁|DuPont", re.IGNORECASE), "fin"),
    (re.compile(r"밸류에이션|가정"), "val"),
    (re.compile(r"가격\s*(탭|시트)|시트\s*가격"), "px"),
    (re.compile(r"뉴스|기사"), "news:1"),
    (re.compile(r"유튜브|YouTube|영상", re.IGNORECASE), "yt:1"),
    (re.compile(r"리포트|보고서"), "rpt"),
    (re.compile(r"시장|시세|지수"), "mkt"),
    (re.compile(r"pepper|페퍼|점수", re.IGNORECASE), "pep"),
]


def match_view(text: str) -> str | None:
    """'포트폴리오 보여줘' 같은 짧은 조회 요청이면 화면 키를 돌려줍니다. 분석 질문은 None."""
    t = (text or "").strip()
    if not t or len(t) > 40 or not _SHOW.search(t):
        return None
    for pattern, key in _INTENTS:
        if pattern.search(t):
            return key
    return None
