from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from shared.config import CONFIG


async def style_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("📊 Professional", callback_data="style_professional"),
         InlineKeyboardButton("🎯 Aggressive",   callback_data="style_aggressive")],
        [InlineKeyboardButton("🛡️ Conservative",  callback_data="style_conservative"),
         InlineKeyboardButton("⚖️ Balanced",      callback_data="style_balanced")],
        [InlineKeyboardButton("💼 Druckenmiller", callback_data="style_druckenmiller")],
    ]
    current = CONFIG.get("report_style", "aggressive")
    await update.message.reply_text(
        f"현재: {current}\n리포트 스타일을 선택하세요:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def api_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🔍 DeepSeek", callback_data="api_deepseek"),
         InlineKeyboardButton("⚡ Groq",     callback_data="api_groq")],
        [InlineKeyboardButton("🌟 Gemini",   callback_data="api_gemini"),
         InlineKeyboardButton("🤖 Claude",   callback_data="api_claude")],
    ]
    current = CONFIG.get("llm_provider", "deepseek")
    await update.message.reply_text(
        f"현재: {current}\nAI 제공자를 선택하세요:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    scheduler = context.bot_data.get("scheduler")
    yt_count  = sum(len(v) for v in CONFIG.get("youtube_channels", {}).values())
    await update.message.reply_text(
        f"📊 봇 상태\n\n"
        f"🤖 AI: {CONFIG.get('llm_provider', 'deepseek')}\n"
        f"📝 스타일: {CONFIG.get('report_style', 'aggressive')}\n"
        f"⏰ 리포트: {CONFIG.get('schedule', {}).get('daily_report_time', '08:00')} KST\n\n"
        f"📺 YouTube 채널: {yt_count}개\n"
        f"🌐 RSS 피드: {len(CONFIG.get('rss_feeds', []))}개\n"
        f"👥 수신자: {len(CONFIG.get('report_recipients', []))}명\n\n"
        f"스케줄러: {'✅ 실행 중' if scheduler else '❌ 없음'}"
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data.startswith("style_"):
        style = data.split("_", 1)[1]
        CONFIG["report_style"] = style
        # 스케줄러 분석기도 즉시 반영
        scheduler = context.bot_data.get("scheduler")
        if scheduler and hasattr(scheduler, "analyzer"):
            scheduler.analyzer.style = style
        await query.edit_message_text(f"✅ 스타일 변경: {style}")

    elif data.startswith("api_"):
        provider = data.split("_", 1)[1]
        CONFIG["llm_provider"] = provider
        await query.edit_message_text(f"✅ AI 변경: {provider}\n다음 실행부터 적용됩니다.")
