import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Claude LLM 초기화
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
    temperature=0.7,
    max_tokens=2000
)

# Wikipedia 도구
wikipedia = WikipediaQueryRun(
    api_wrapper=WikipediaAPIWrapper(lang="ko", top_k_results=2)
)

# 대화 기록 저장
conversation_history = {}

# 시스템 프롬프트
SYSTEM_PROMPT = """당신은 OpenClaw 기반 AI 어시스턴트입니다.

사용자의 질문에 정확하고 도움이 되는 답변을 제공하세요.

도구 사용 규칙:
1. Wikipedia 검색이 필요하면 먼저 검색을 수행하세요.
2. 검색 결과를 바탕으로 상세한 답변을 제공하세요.
3. 검색이 필요없는 일반적인 질문은 바로 답변하세요.

사용 가능한 도구:
- Wikipedia 검색 (한국어)
"""

def search_wikipedia(query: str) -> str:
    """Wikipedia 검색 수행"""
    try:
        result = wikipedia.run(query)
        return f"📚 Wikipedia 검색 결과:\n\n{result}"
    except Exception as e:
        return f"검색 중 오류 발생: {str(e)}"

def should_use_wikipedia(message: str) -> bool:
    """Wikipedia 검색이 필요한지 판단"""
    keywords = [
        "검색", "찾아", "알려줘", "뭐야", "무엇", "누구", "언제", 
        "어디", "어떻게", "왜", "정보", "설명", "대해", "관해",
        "wikipedia", "wiki", "백과사전"
    ]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in keywords)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """봇 시작 명령어"""
    user_id = update.effective_user.id
    conversation_history[user_id] = []
    
    await update.message.reply_text(
        "🤖 OpenClaw AI Agent입니다!\n\n"
        "저는 Wikipedia 검색 기능을 활용할 수 있는 AI 어시스턴트입니다.\n\n"
        "명령어:\n"
        "/start - 봇 시작\n"
        "/clear - 대화 기록 초기화\n"
        "/help - 도움말\n"
        "/search [검색어] - Wikipedia 검색\n\n"
        "예시:\n"
        "- 파이썬에 대해 알려줘\n"
        "- 양자컴퓨터 검색해줘\n"
        "- /search 블록체인"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """대화 기록 초기화"""
    user_id = update.effective_user.id
    conversation_history[user_id] = []
    await update.message.reply_text("✅ 대화 기록이 초기화되었습니다.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """도움말"""
    await update.message.reply_text(
        "🔧 OpenClaw AI Agent 기능:\n\n"
        "1. 🧠 대화 컨텍스트 유지\n"
        "2. 📚 Wikipedia 검색 (한국어)\n"
        "3. 🤔 복잡한 질문 처리\n"
        "4. 🔍 자동 검색 판단\n\n"
        "사용법:\n"
        "- 자유롭게 질문하세요 (자동으로 검색 여부 판단)\n"
        "- /search 명령어로 직접 Wikipedia 검색\n\n"
        "예시:\n"
        "- 양자컴퓨터에 대해 조사해줘\n"
        "- 한국의 역사를 알려줘\n"
        "- /search 인공지능"
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wikipedia 검색 명령어"""
    if not context.args:
        await update.message.reply_text(
            "사용법: /search [검색어]\n\n"
            "예시: /search 양자컴퓨터"
        )
        return
    
    query = " ".join(context.args)
    await update.message.chat.send_action("typing")
    
    try:
        result = search_wikipedia(query)
        
        # 결과가 너무 길면 나누어 전송
        if len(result) > 4000:
            parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ 검색 오류: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """메시지 처리"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # 사용자별 대화 기록 초기화
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    # "입력중..." 표시
    await update.message.chat.send_action("typing")
    
    try:
        # Wikipedia 검색이 필요한지 판단
        wiki_result = None
        if should_use_wikipedia(user_message):
            logger.info(f"Wikipedia 검색 수행: {user_message}")
            wiki_result = search_wikipedia(user_message)
        
        # 대화 메시지 구성
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        # 이전 대화 기록 추가 (최근 10개만)
        messages.extend(conversation_history[user_id][-10:])
        
        # Wikipedia 검색 결과가 있으면 추가
        if wiki_result:
            messages.append(HumanMessage(
                content=f"다음 Wikipedia 검색 결과를 참고하여 질문에 답변해주세요.\n\n{wiki_result}\n\n질문: {user_message}"
            ))
        else:
            messages.append(HumanMessage(content=user_message))
        
        # Claude API 호출
        response = llm.invoke(messages)
        ai_response = response.content
        
        # 대화 기록에 추가
        conversation_history[user_id].append(HumanMessage(content=user_message))
        conversation_history[user_id].append(AIMessage(content=ai_response))
        
        # 대화 기록 길이 제한 (최근 20개 메시지만 유지)
        if len(conversation_history[user_id]) > 20:
            conversation_history[user_id] = conversation_history[user_id][-20:]
        
        # 응답 전송
        if len(ai_response) > 4000:
            parts = [ai_response[i:i+4000] for i in range(0, len(ai_response), 4000)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(ai_response)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            f"❌ 오류가 발생했습니다: {str(e)}\n\n"
            "잠시 후 다시 시도해주세요."
        )

def main():
    """봇 실행"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다!")
        return
    
    # Application 생성
    application = Application.builder().token(token).build()
    
    # 핸들러 등록
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 봇 시작
    logger.info("🚀 OpenClaw-style Telegram Agent started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
