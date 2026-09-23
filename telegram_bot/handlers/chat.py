from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = context.bot_data["chat"]
    chat.clear(update.effective_user.id)
    await update.message.reply_text(
        "🤖 Edgar AI 봇\n\n"
        "명령어:\n"
        "/monitor — 즉시 시장 분석 실행\n"
        "/report  — 최근 리포트 조회\n"
        "/style   — 분석 스타일 변경\n"
        "/api     — AI 제공자 변경\n"
        "/status  — 봇 상태\n"
        "/pepper  — Pepper 4대가 결과 요약\n"
        "/stock   — 종목 점수표 + Astra 분석\n"
        "/budget  — Astra 월 사용액\n"
        "/clear   — 대화 기록 초기화\n\n"
        "💬 자유롭게 질문하세요!"
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot_data["chat"].clear(update.effective_user.id)
    await update.message.reply_text("대화 기록이 초기화되었습니다.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 사용법:\n\n"
        "• 자유롭게 메시지 → Gemini(무료)와 대화, 종목 분석 질문은 GPT-6 Astra\n"
        "• /monitor → 지금 바로 시장 분석 리포트 생성\n"
        "• /report  → 마지막으로 저장된 리포트 보기\n"
        "• /style   → 리포트 스타일 선택 (5가지)\n"
        "• /api     → LLM 제공자 선택\n"
        "• /status  → 현재 설정 및 스케줄 상태\n"
        "• /pepper  → Pepper 결과 요약 (모델 호출 없음)\n"
        "• /stock NVDA → 4대가 점수표 + Astra 해석\n"
        "• /budget  → 이번 달 Astra 사용액 / $20 상한\n"
        "• /rules   → 규칙 버전\n"
        "• /clear   → 대화 이력 초기화"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = context.bot_data["chat"]
    await update.message.chat.send_action("typing")
    answer = await chat.reply(update.effective_user.id, update.message.text)
    await update.message.reply_text(answer)
