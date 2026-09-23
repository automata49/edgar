"""/pepper, /stock, /budget 명령: Pepper 계산 결과 조회와 Astra 분석."""
from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from invest import pepper_results


def _results(context: ContextTypes.DEFAULT_TYPE) -> dict | None:
    return pepper_results.load(context.bot_data["chat"].results_path)


async def _send_long(update: Update, text: str) -> None:
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i + 4000])


async def pepper_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """오늘 Pepper 결과 요약 (모델 호출 없음)."""
    results = _results(context)
    if not results:
        await update.message.reply_text("Pepper 결과 파일이 없습니다. pepper score를 먼저 실행하세요.")
        return
    await _send_long(update, "\n".join(pepper_results.summary_lines(results)))


async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stock TICKER [질문] → 점수표 + GPT-6 Astra 해석."""
    if not context.args:
        await update.message.reply_text("사용법: /stock NVDA [질문]")
        return
    ticker = context.args[0].upper()
    results = _results(context)
    r = (results or {}).get("tickers", {}).get(ticker)
    if not r:
        await update.message.reply_text(f"{ticker}의 Pepper 결과가 없습니다.")
        return
    await update.message.reply_text(pepper_results.ticker_card(ticker, r))
    await update.message.chat.send_action("typing")
    chat = context.bot_data["chat"]
    result = await asyncio.to_thread(chat.analyze, ticker, " ".join(context.args[1:]))
    tail = f"\n\n— {result.model or '모델 없음'}" + (f" · ${result.cost_usd:.3f}" if result.cost_usd else "")
    if result.downgraded and result.ok:
        tail += " (대체 모델)"
    await _send_long(update, result.text + tail)


async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = context.bot_data["chat"].router.budget_status()
    await update.message.reply_text(
        f"💰 {s['month']} Astra 사용액 ${s['spent_usd']:.2f} / 상한 ${s['limit_usd']:.0f}\n"
        f"남은 금액 ${s['remaining_usd']:.2f}" + ("\n80% 초과: reasoning low로 실행 중" if s["soft_limited"] else ""))


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    results = _results(context)
    if not results:
        await update.message.reply_text("Pepper 결과 파일이 없습니다.")
        return
    v = results.get("rules_version", {})
    await update.message.reply_text("📐 규칙 버전\n" + "\n".join(f"• {k}: {x}" for k, x in v.items()))
