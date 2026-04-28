"""telegram_bot 진입점."""
from __future__ import annotations

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from shared.config import CONFIG
from database.client import SupabaseDB
from kstock_signal.scheduler import SignalScheduler
from telegram_bot.services.claude_chat import ClaudeChat
from telegram_bot.handlers.chat import (
    clear_command, handle_message, help_command, start_command,
)
from telegram_bot.handlers.signal import monitor_command, report_command
from telegram_bot.handlers.settings_handler import (
    api_command, callback_handler, status_command, style_command,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_db() -> SupabaseDB | None:
    url, key = CONFIG.get("supabase_url"), CONFIG.get("supabase_key")
    if url and key:
        logger.info("✅ Supabase 연결")
        return SupabaseDB(url, key)
    logger.warning("⚠️  Supabase 비활성")
    return None


def create_app() -> Application:
    token = CONFIG.get("telegram_bot_token")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN 이 설정되지 않았습니다.")

    app = Application.builder().token(token).build()

    # 공유 객체
    db = build_db()
    app.bot_data["claude_chat"] = ClaudeChat(CONFIG.get("anthropic_api_key", ""))
    app.bot_data["scheduler"]   = SignalScheduler(CONFIG, bot=app.bot, db=db)
    app.bot_data["db"]          = db

    # 핸들러 등록
    app.add_handler(CommandHandler("start",   start_command))
    app.add_handler(CommandHandler("help",    help_command))
    app.add_handler(CommandHandler("clear",   clear_command))
    app.add_handler(CommandHandler("monitor", monitor_command))
    app.add_handler(CommandHandler("report",  report_command))
    app.add_handler(CommandHandler("style",   style_command))
    app.add_handler(CommandHandler("api",     api_command))
    app.add_handler(CommandHandler("status",  status_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app


async def _run() -> None:
    app       = create_app()
    scheduler = app.bot_data["scheduler"]

    if CONFIG.get("schedule", {}).get("enabled", True):
        # 봇 초기화 후 스케줄러 시작
        async with app:
            scheduler.start()
            await app.start()
            await app.updater.start_polling()
            logger.info("Edgar 봇 실행 중...")
            await asyncio.Event().wait()
    else:
        app.run_polling()


def main() -> None:
    try:
        asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("봇 종료")


if __name__ == "__main__":
    main()
