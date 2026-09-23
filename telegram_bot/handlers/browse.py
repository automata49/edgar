"""/view — Google 시트(Pepper)와 수집 데이터를 인라인 버튼으로 둘러보기.

버튼을 누르면 같은 메시지가 해당 화면으로 바뀌어(edit) 대화가 어지럽지 않습니다.
callback_data 형식: v:<화면>[:<인자>][:r]  (r = 새로고침)
"""
from __future__ import annotations

import asyncio
import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from invest import pepper_results, views
from shared.config import CONFIG

logger = logging.getLogger(__name__)

_SHEET_HINT = ("Google 시트 인증(GOOGLE_APPLICATION_CREDENTIALS)을 설정하거나 "
               "Pepper에서 `pepper sync`를 한 번 실행해 스냅샷을 만드세요.")
_DB_HINT = "SUPABASE_URL / SUPABASE_KEY 가 설정되지 않았습니다."


def allowed_ids() -> set[int]:
    ids = CONFIG.get("telegram_allowed_ids") or [i for i in CONFIG.get("report_recipients", []) if i > 0]
    return set(ids)


def is_allowed(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id in allowed_ids()


def _markup(page: views.Page) -> InlineKeyboardMarkup | None:
    rows = []
    for row in page.buttons:
        rows.append([InlineKeyboardButton(label, url=data[4:]) if data.startswith("url:")
                     else InlineKeyboardButton(label, callback_data=data) for label, data in row])
    return InlineKeyboardMarkup(rows) if rows else None


async def _load_sheet(context: ContextTypes.DEFAULT_TYPE, refresh: bool = False) -> dict | None:
    reader = context.bot_data.get("sheets")
    return await asyncio.to_thread(reader.load, refresh) if reader else None


async def _db_call(context: ContextTypes.DEFAULT_TYPE, method: str, *args):
    db = context.bot_data.get("db")
    if db is None:
        return None
    try:
        return await asyncio.to_thread(getattr(db, method), *args)
    except Exception as e:  # noqa: BLE001 — DB 장애로 봇이 멈추지 않도록
        logger.warning("DB 조회 실패 %s: %s", method, e)
        return None


async def build_page(context: ContextTypes.DEFAULT_TYPE, key: str) -> views.Page:
    """'pf', 'pf:NVDA', 'news:2', 'rs:r' 같은 키 → Page."""
    parts = key.split(":")
    refresh = parts[-1] == "r"
    if refresh:
        parts = parts[:-1]
    view, arg = parts[0], (parts[1] if len(parts) > 1 else None)
    reader = context.bot_data.get("sheets")

    if view == "home":
        return views.home(reader.url if reader else None)

    if view in ("pf", "rs", "fin", "val", "px"):
        sheet = await _load_sheet(context, refresh)
        if not sheet:
            return views.unavailable("Google 시트", _SHEET_HINT)
        if view == "pf":
            return views.portfolio_detail(sheet, arg) if arg else views.portfolio(sheet)
        if view == "rs":
            return views.research_detail(sheet, arg) if arg else views.research(sheet)
        if view == "fin":
            return views.financials(sheet, arg)
        return views.valuation(sheet) if view == "val" else views.prices(sheet)

    if view == "pep":
        results = pepper_results.load(context.bot_data["chat"].results_path)
        return views.pepper_detail(results, arg) if arg else views.pepper(results)

    if view in ("news", "yt"):
        if context.bot_data.get("db") is None:
            return views.unavailable("수집 데이터", _DB_HINT)
        page = int(arg) if arg and arg.isdigit() else 1
        if view == "news":
            return views.news(await _db_call(context, "recent_news", 40) or [], page)
        return views.videos(await _db_call(context, "recent_videos", 40) or [], page)

    if view in ("rr", "wk"):
        if context.bot_data.get("db") is None:
            return views.unavailable("증권사 리포트" if view == "rr" else "Weekly 리포트", _DB_HINT)
        if view == "wk":
            return views.weekly(await _db_call(context, "latest_report_of", "weekly"))
        if arg:
            return views.research_reports(await _db_call(context, "research_by_stock", arg, 8) or [], arg)
        return views.research_stocks(await _db_call(context, "research_stocks", 60) or [])

    if view in ("mkt", "rpt"):
        rep = await _db_call(context, "latest_report")
        if view == "mkt":
            try:
                from kstock_signal.collectors.market import CATEGORY_MAP
            except ImportError:   # yfinance 미설치 등 — 분류 없이 표시
                CATEGORY_MAP = {}
            if rep is None:
                return views.unavailable("시장 데이터", _DB_HINT if context.bot_data.get("db") is None
                                         else "저장된 리포트가 없습니다. /monitor 로 수집하세요.")
            return views.market(rep.get("market_snapshot") or {}, CATEGORY_MAP, rep.get("created_at"), arg)
        fallback = None if rep else await asyncio.to_thread(_read_tmp_report)
        return views.report(rep, fallback)

    return views.home(reader.url if reader else None)


def _read_tmp_report() -> str | None:
    """DB가 없을 때 /report 와 같은 로컬 캐시를 사용합니다."""
    try:
        with open("/tmp/latest_report.txt", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


async def send_page(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str) -> None:
    page = await build_page(context, key)
    await update.effective_message.reply_text(page.text, parse_mode=ParseMode.HTML,
                                              reply_markup=_markup(page), disable_web_page_preview=True)


async def view_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/view [pf|rs|fin|val|px|mkt|news|yt|rpt|wk|rr|pep] [TICKER|종목]"""
    if not is_allowed(update):
        await update.message.reply_text("🔒 이 명령은 등록된 사용자만 쓸 수 있습니다.")
        return
    args = [a for a in (context.args or []) if a]
    view = args[0].lower() if args else "home"
    arg = args[1] if len(args) > 1 else None
    if arg:
        if view == "mkt":
            arg = arg.lower()                      # 시장 분류는 소문자
        elif view != "rr":
            arg = arg.upper()                      # 티커는 대문자 (rr 은 한글 종목명 그대로)
    key = f"{view}:{arg}" if arg else view
    if key in ("news", "yt"):
        key += ":1"
    await send_page(update, context, key)


async def view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""
    if not is_allowed(update):
        await query.answer("🔒 권한이 없습니다", show_alert=True)
        return
    if data == "v:noop":
        await query.answer()
        return
    if data.startswith("v:ai:"):
        await query.answer("AI 해석을 요청했습니다…")
        await _ai_reply(update, context, data[5:])
        return
    await query.answer("새로고침…" if data.endswith(":r") else None)
    page = await build_page(context, data[2:])
    try:
        await query.edit_message_text(page.text, parse_mode=ParseMode.HTML, reply_markup=_markup(page),
                                      disable_web_page_preview=True)
    except BadRequest as e:
        if "not modified" not in str(e).lower():   # 같은 화면을 다시 누른 경우는 무시
            raise


async def _ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, ticker: str) -> None:
    msg = update.effective_message
    await msg.chat.send_action("typing")
    result = await asyncio.to_thread(context.bot_data["chat"].analyze, ticker, "")
    tail = f"\n\n— {result.model or '모델 없음'}" + (f" · ${result.cost_usd:.3f}" if result.cost_usd else "")
    if result.downgraded and result.ok:
        tail += " (대체 모델)"
    text = result.text + tail
    for i in range(0, len(text), 4000):
        await msg.reply_text(text[i:i + 4000])


_TICKER = re.compile(r"[A-Za-z0-9_.]{2,12}")
_WORD = re.compile(r"[가-힣A-Za-z0-9&]+")
_NOT_STOCK = re.compile(r"^(증권사|리서치|리포트|보고서|애널리스트|목표|주가|목표주가|최근|오늘|이번|주|좀|요약|"
                        r"보여.*|확인.*|알려.*|조회.*|봐.*|볼래|열어.*|정리.*|현황|목록)$")
_JOSA = re.compile(r"(의|를|을|은|는|이|가|에|도)$")


def _stock_from_text(text: str) -> str | None:
    """'삼성전자 증권사 리포트 보여줘' → '삼성전자'. 종목으로 볼 단어가 없으면 None."""
    for w in _WORD.findall(text):
        w = _JOSA.sub("", w) if len(w) > 2 else w
        if len(w) >= 2 and not _NOT_STOCK.match(w):
            return w[:15]
    return None


async def try_view_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """자유 대화 중 '포트폴리오 보여줘' 같은 조회 요청이면 화면을 보내고 True."""
    text = update.message.text or ""
    key = views.match_view(text)
    if key is None or not is_allowed(update):
        return False
    if key == "rr" and (stock := _stock_from_text(text)):
        key = f"rr:{stock}"
    if key in ("pf", "rs", "fin", "pep"):
        words = {w.upper() for w in _TICKER.findall(text)}
        known: set[str] = set()
        if key == "pep":
            known = set((pepper_results.load(context.bot_data["chat"].results_path) or {}).get("tickers", {}))
        else:
            sheet = await _load_sheet(context)
            tab = {"pf": "Portfolio", "rs": "Research", "fin": "Financials"}[key]
            known = {str(r.get("Ticker")).upper() for r in (sheet or {}).get("tables", {}).get(tab, [])}
        hit = sorted(words & known)
        if hit:
            key = f"{key}:{hit[0]}"
    await send_page(update, context, key)
    return True


async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/research [종목명|코드] — 증권사 리포트 종목별 목록 또는 한 종목 상세."""
    if not is_allowed(update):
        await update.message.reply_text("🔒 이 명령은 등록된 사용자만 쓸 수 있습니다.")
        return
    query = " ".join(context.args or []).strip()
    await send_page(update, context, f"rr:{query}" if query else "rr")


async def weekly_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/weekly — 지난 7일 Weekly 리포트를 지금 만들어 요청한 채팅으로 보냅니다."""
    if not is_allowed(update):
        await update.message.reply_text("🔒 이 명령은 등록된 사용자만 쓸 수 있습니다.")
        return
    scheduler = context.bot_data.get("scheduler")
    if scheduler is None or context.bot_data.get("db") is None:
        await update.message.reply_text("⚠️ Weekly 리포트는 Supabase에 저장된 데이터가 필요합니다.")
        return
    await update.message.reply_text("🗓 Weekly 리포트를 만드는 중입니다… (30초~1분)")
    try:
        report = await scheduler.run_weekly(chat_ids=[update.effective_chat.id])
    except Exception as e:  # noqa: BLE001 — 봇이 멈추지 않도록
        logger.warning("Weekly 생성 실패: %s", e)
        report = None
    if report is None:
        await update.message.reply_text("⚠️ Weekly 리포트를 만들지 못했습니다. 로그를 확인하세요.")
