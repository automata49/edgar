import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from anthropic import Anthropic
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API 클라이언트 초기화
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# 대화 기록 저장 (메모리)
conversation_history = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """봇 시작 명령어"""
    user_id = update.effective_user.id
    conversation_history[user_id] = []
    
    await update.message.reply_text(
        "안녕하세요! Claude AI 챗봇입니다. 무엇을 도와드릴까요?\n\n"
        "명령어:\n"
        "/start - 봇 시작\n"
        "/clear - 대화 기록 초기화\n"
        "/help - 도움말"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """대화 기록 초기화"""
    user_id = update.effective_user.id
    conversation_history[user_id] = []
    await update.message.reply_text("대화 기록이 초기화되었습니다.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """도움말"""
    await update.message.reply_text(
        "Claude AI 챗봇 사용법:\n\n"
        "1. 자유롭게 질문하거나 대화하세요\n"
        "2. 이전 대화 내용을 기억합니다\n"
        "3. /clear로 대화 기록을 초기화할 수 있습니다\n\n"
        "예시:\n"
        "- Python으로 웹 크롤링하는 방법 알려줘\n"
        "- 오늘 날씨 어때?\n"
        "- 영어로 번역해줘: 안녕하세요"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """메시지 처리"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # 사용자별 대화 기록 초기화
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    # 대화 기록에 사용자 메시지 추가
    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })
    
    # "입력중..." 표시
    await update.message.chat.send_action("typing")
    
    try:
        # Claude API 호출
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=conversation_history[user_id]
        )
        
        # 응답 추출
        ai_response = response.content[0].text
        
        # 대화 기록에 AI 응답 추가
        conversation_history[user_id].append({
            "role": "assistant",
            "content": ai_response
        })
        
        # 대화 기록 길이 제한 (최근 20개 메시지만 유지)
        if len(conversation_history[user_id]) > 20:
            conversation_history[user_id] = conversation_history[user_id][-20:]
        
        # 응답 전송
        await update.message.reply_text(ai_response)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            f"오류가 발생했습니다: {str(e)}\n\n"
            "잠시 후 다시 시도해주세요."
        )

def main():
    """봇 실행"""
    # 봇 토큰
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Application 생성
    application = Application.builder().token(token).build()
    
    # 핸들러 등록
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 봇 시작
    logger.info("Bot started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
