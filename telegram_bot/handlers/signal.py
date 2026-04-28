from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


async def monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """즉시 시장 분석 실행."""
    scheduler = context.bot_data.get("scheduler")
    if not scheduler:
        await update.message.reply_text("❌ 스케줄러가 초기화되지 않았습니다.")
        return

    await update.message.reply_text("🚀 시장 분석을 시작합니다... (1-3분 소요)")
    try:
        result = await scheduler.run()
        stats  = result.get("stats", {})
        await update.message.reply_text(
            f"✅ 분석 완료\n"
            f"• YouTube: {stats.get('youtube_count', 0)}개\n"
            f"• 뉴스: {stats.get('website_count', 0)}개\n\n"
            "리포트가 수신자에게 발송되었습니다."
        )
    except Exception as e:
        await update.message.reply_text(f"❌ 실패: {e}")


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tmp/latest_report.txt 내용 전송."""
    try:
        with open("/tmp/latest_report.txt", encoding="utf-8") as f:
            content = f.read()
        # 4096자 제한
        for i in range(0, min(len(content), 8000), 4000):
            await update.message.reply_text(content[i:i + 4000])
    except FileNotFoundError:
        await update.message.reply_text("저장된 리포트가 없습니다. /monitor 로 먼저 실행하세요.")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")
