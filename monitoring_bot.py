import asyncio
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from telegram.error import BadRequest
from config import CONFIG

# 전역 변수
scheduler = None
conversation_history = {}

# === 명령어 핸들러 ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """시작 명령어"""
    welcome_text = """
🤖 OpenClaw AI 트렌드 분석 봇

📺 YouTube 채널 모니터링
🌐 웹사이트/RSS 수집
📊 실시간 시장 데이터
🤖 AI 트렌드 분석

사용 가능한 명령어:
/help - 도움말
/monitor - 즉시 리포트 생성
/style - 리포트 스타일 변경
/api - AI 제공자 변경
/status - 봇 상태 확인
/config - 현재 설정 보기
/ask - AI에게 질문
/reset - 대화 이력 초기화

💬 일반 메시지를 보내면 AI와 대화할 수 있습니다!
"""
    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """도움말"""
    help_text = """
📖 명령어 가이드:

/monitor - 즉시 리포트 생성
/style - 리포트 스타일 변경
  • Professional: 객관적, 데이터 중심
  • Aggressive: 적극적, 액션 지향
  • Conservative: 신중, 리스크 관리
  • Balanced: 균형잡힌 시각
  • Druckenmiller: 매크로 집중, 포지션 사이징

/api - AI 제공자 변경
  • DeepSeek V3.2 (기본)
  • Groq (빠름)
  • Gemini (구글)
  • Claude (Anthropic)

/status - 수집 상태 확인
/config - 현재 설정
/chatid - 채팅 ID 확인
/ask [질문] - AI에게 질문
/reset - 대화 이력 초기화

💬 일반 메시지: AI와 자유 대화
"""
    await update.message.reply_text(help_text)


async def monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """즉시 모니터링 실행"""
    global scheduler
    
    await update.message.reply_text("🚀 모니터링을 시작합니다...")
    
    if scheduler:
        try:
            await scheduler.run_monitoring_task()
        except Exception as e:
            await update.message.reply_text(f"❌ 모니터링 실패: {str(e)}")
    else:
        await update.message.reply_text("❌ 스케줄러가 초기화되지 않았습니다.")


async def style_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """리포트 스타일 변경"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Professional", callback_data='style_professional'),
            InlineKeyboardButton("🎯 Aggressive", callback_data='style_aggressive'),
        ],
        [
            InlineKeyboardButton("🛡️ Conservative", callback_data='style_conservative'),
            InlineKeyboardButton("⚖️ Balanced", callback_data='style_balanced'),
        ],
        [
            InlineKeyboardButton("💼 Druckenmiller", callback_data='style_druckenmiller'),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_style = CONFIG.get('report_style', 'professional')
    await update.message.reply_text(
        f"현재 스타일: {current_style}\n\n리포트 스타일을 선택하세요:",
        reply_markup=reply_markup
    )


async def api_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI 제공자 변경"""
    keyboard = [
        [
            InlineKeyboardButton("🔍 DeepSeek", callback_data='api_deepseek'),
            InlineKeyboardButton("⚡ Groq", callback_data='api_groq'),
        ],
        [
            InlineKeyboardButton("🌟 Gemini", callback_data='api_gemini'),
            InlineKeyboardButton("🤖 Claude", callback_data='api_claude'),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_api = CONFIG.get('llm_provider', 'deepseek')
    await update.message.reply_text(
        f"현재 AI: {current_api}\n\nAI 제공자를 선택하세요:",
        reply_markup=reply_markup
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """봇 상태 확인"""
    global scheduler
    
    status_text = f"""
📊 봇 상태

🤖 AI: {CONFIG.get('llm_provider', 'deepseek')}
📝 스타일: {CONFIG.get('report_style', 'professional')}
⏰ 스케줄: {"활성" if CONFIG.get('schedule', {}).get('enabled') else "비활성"}
🕐 리포트 시간: {CONFIG.get('schedule', {}).get('daily_report_time', '08:00')}

📺 YouTube 채널: {sum(len(v) for v in CONFIG.get('youtube_channels', {}).values())}개
🌐 RSS 피드: {len(CONFIG.get('rss_feeds', []))}개
👥 수신자: {len(CONFIG.get('report_recipients', []))}명

스케줄러: {"✅ 실행 중" if scheduler else "❌ 중지"}
"""
    await update.message.reply_text(status_text)


async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """현재 설정 보기"""
    import json
    
    safe_config = {
        'llm_provider': CONFIG.get('llm_provider'),
        'report_style': CONFIG.get('report_style'),
        'youtube_channels': {k: len(v) for k, v in CONFIG.get('youtube_channels', {}).items()},
        'rss_feeds_count': len(CONFIG.get('rss_feeds', [])),
        'schedule': CONFIG.get('schedule'),
        'collection_timeframes': CONFIG.get('collection_timeframes')
    }
    
    config_text = f"""
⚙️ 현재 설정
```json
{json.dumps(safe_config, indent=2, ensure_ascii=False)}
```
"""
    await update.message.reply_text(config_text)


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """채팅 ID 확인"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    info_text = f"""
🆔 채팅 정보

Chat ID: `{chat_id}`
User ID: `{user_id}`
Chat Type: {update.effective_chat.type}

리포트 수신 설정에 사용하세요!
"""
    await update.message.reply_text(info_text)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI에게 질문"""
    global conversation_history
    
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("사용법: /ask [질문]\n\n예: /ask 비트코인 전망은?")
        return
    
    question = ' '.join(context.args)
    
    # 대화 이력 가져오기
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    # 최신 리포트 로드
    report_context = ""
    try:
        with open('/tmp/latest_report.txt', 'r', encoding='utf-8') as f:
            report_context = f.read()
    except:
        pass
    
    # AI 호출
    provider = CONFIG.get('llm_provider', 'deepseek')
    
    try:
        conversation_history[user_id].append({"role": "user", "content": question})
        
        if provider == 'deepseek':
            answer = call_deepseek(conversation_history[user_id], report_context)
        elif provider == 'groq':
            answer = call_groq(conversation_history[user_id], report_context)
        elif provider == 'gemini':
            answer = call_gemini(conversation_history[user_id], report_context)
        elif provider == 'claude':
            answer = call_claude(conversation_history[user_id], report_context)
        else:
            answer = "지원하지 않는 AI 제공자입니다."
        
        conversation_history[user_id].append({"role": "assistant", "content": answer})
        
        # 대화 이력 최대 10턴 유지
        if len(conversation_history[user_id]) > 20:
            conversation_history[user_id] = conversation_history[user_id][-20:]
        
        await update.message.reply_text(answer)
        
    except Exception as e:
        await update.message.reply_text(f"❌ AI 응답 실패: {str(e)}")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """대화 이력 초기화"""
    global conversation_history
    
    user_id = update.effective_user.id
    
    if user_id in conversation_history:
        del conversation_history[user_id]
    
    await update.message.reply_text("✅ 대화 이력이 초기화되었습니다.")


# === 콜백 핸들러 ===

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """통합 콜백 핸들러"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # 스타일 변경
    if data.startswith('style_'):
        await style_callback(query, context)
    
    # API 변경
    elif data.startswith('api_'):
        await api_callback(query, context)


async def style_callback(query, context):
    """스타일 선택 콜백"""
    style_map = {
        'style_professional': 'professional',
        'style_aggressive': 'aggressive',
        'style_conservative': 'conservative',
        'style_balanced': 'balanced',
        'style_druckenmiller': 'druckenmiller'
    }
    
    style_names = {
        'professional': '📊 Professional (객관적, 데이터 중심)',
        'aggressive': '🎯 Aggressive (적극적, 액션 지향)',
        'conservative': '🛡️ Conservative (신중, 리스크 관리)',
        'balanced': '⚖️ Balanced (균형잡힌 시각)',
        'druckenmiller': '💼 Druckenmiller (매크로 집중, 포지션 사이징)'
    }
    
    selected_style = style_map.get(query.data)
    
    if selected_style:
        CONFIG['report_style'] = selected_style
        
        # config.py 파일 업데이트
        update_config_file('report_style', selected_style)
        
        await query.edit_message_text(
            f"✅ 리포트 스타일이 변경되었습니다!\n\n{style_names[selected_style]}\n\n다음 리포트부터 적용됩니다."
        )


async def api_callback(query, context):
    """API 선택 콜백"""
    api_map = {
        'api_deepseek': 'deepseek',
        'api_groq': 'groq',
        'api_gemini': 'gemini',
        'api_claude': 'claude'
    }
    
    api_names = {
        'deepseek': '🔍 DeepSeek V3.2 (기본)',
        'groq': '⚡ Groq Llama 3.3 70B',
        'gemini': '🌟 Google Gemini Pro',
        'claude': '🤖 Anthropic Claude Sonnet'
    }
    
    selected_api = api_map.get(query.data)
    
    if selected_api:
        CONFIG['llm_provider'] = selected_api
        
        # config.py 파일 업데이트
        update_config_file('llm_provider', selected_api)
        
        await query.edit_message_text(
            f"✅ AI 제공자가 변경되었습니다!\n\n{api_names[selected_api]}\n\n다음 분석부터 적용됩니다."
        )


def update_config_file(key, value):
    """config.py 파일 업데이트"""
    try:
        with open('config.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 값 업데이트
        if key == 'llm_provider':
            content = content.replace(
                f"'llm_provider': '{CONFIG.get('llm_provider')}'",
                f"'llm_provider': '{value}'"
            )
        elif key == 'report_style':
            content = content.replace(
                f"'report_style': '{CONFIG.get('report_style')}'",
                f"'report_style': '{value}'"
            )
        
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write(content)
            
    except Exception as e:
        print(f"⚠️ config.py 업데이트 실패: {e}")


# === LLM 호출 함수 ===

def call_deepseek(messages, report_context=""):
    """DeepSeek 호출"""
    from openai import OpenAI
    
    client = OpenAI(
        api_key=CONFIG['deepseek_api_key'],
        base_url="https://api.deepseek.com"
    )
    
    system_prompt = f"""당신은 금융 트렌드 분석 전문가입니다.
최신 리포트를 참고하여 답변하세요.

=== 최신 리포트 ===
{report_context[:3000] if report_context else "리포트 없음"}
"""
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            *messages
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content


def call_groq(messages, report_context=""):
    """Groq 호출"""
    from groq import Groq
    
    client = Groq(api_key=CONFIG['groq_api_key'])
    
    system_prompt = f"""당신은 금융 트렌드 분석 전문가입니다.
최신 리포트를 참고하여 답변하세요.

=== 최신 리포트 ===
{report_context[:3000] if report_context else "리포트 없음"}
"""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            *messages
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content


def call_gemini(messages, report_context=""):
    """Gemini 호출"""
    import google.generativeai as genai
    
    genai.configure(api_key=CONFIG['gemini_api_key'])
    model = genai.GenerativeModel('gemini-pro')
    
    # 대화 이력 포맷
    conversation = ""
    for msg in messages:
        role = "사용자" if msg['role'] == 'user' else "AI"
        conversation += f"{role}: {msg['content']}\n\n"
    
    prompt = f"""당신은 금융 트렌드 분석 전문가입니다.

=== 최신 리포트 ===
{report_context[:2000] if report_context else "리포트 없음"}

=== 대화 ===
{conversation}

위 리포트와 대화를 참고하여 답변하세요."""
    
    response = model.generate_content(prompt)
    return response.text


def call_claude(messages, report_context=""):
    """Claude 호출"""
    from anthropic import Anthropic
    
    client = Anthropic(api_key=CONFIG['anthropic_api_key'])
    
    system_prompt = f"""당신은 금융 트렌드 분석 전문가입니다.
최신 리포트를 참고하여 답변하세요.

=== 최신 리포트 ===
{report_context[:3000] if report_context else "리포트 없음"}
"""
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system_prompt,
        messages=messages
    )
    
    return response.content[0].text


# === 일반 메시지 핸들러 ===

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """일반 메시지 처리 (AI 대화)"""
    global conversation_history
    
    user_id = update.effective_user.id
    message = update.message.text
    
    # 대화 이력 초기화
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    # 최신 리포트 로드
    report_context = ""
    try:
        with open('/tmp/latest_report.txt', 'r', encoding='utf-8') as f:
            report_context = f.read()
    except:
        pass
    
    # AI 호출
    provider = CONFIG.get('llm_provider', 'deepseek')
    
    try:
        conversation_history[user_id].append({"role": "user", "content": message})
        
        if provider == 'deepseek':
            answer = call_deepseek(conversation_history[user_id], report_context)
        elif provider == 'groq':
            answer = call_groq(conversation_history[user_id], report_context)
        elif provider == 'gemini':
            answer = call_gemini(conversation_history[user_id], report_context)
        elif provider == 'claude':
            answer = call_claude(conversation_history[user_id], report_context)
        else:
            answer = "지원하지 않는 AI 제공자입니다."
        
        conversation_history[user_id].append({"role": "assistant", "content": answer})
        
        # 대화 이력 최대 10턴 유지
        if len(conversation_history[user_id]) > 20:
            conversation_history[user_id] = conversation_history[user_id][-20:]
        
        await update.message.reply_text(answer)
        
    except Exception as e:
        await update.message.reply_text(f"❌ AI 응답 실패: {str(e)}")


# === 초기화 ===

async def post_init(application: Application):
    """봇 시작 후 초기화"""
    global scheduler
    
    print("\n" + "="*60)
    print("🚀 봇 시작 준비...")
    print("="*60 + "\n")
    
    try:
        # 스케줄러 초기화
        from scheduler import MonitoringScheduler
        
        scheduler = MonitoringScheduler(CONFIG, application.bot)
        
        print("\n🚀 봇 시작 완료!\n")
        
    except Exception as e:
        print(f"\n❌ 초기화 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 함수"""
    print("\n" + "="*60)
    print("🤖 OpenClaw Telegram Bot")
    print("="*60 + "\n")
    
    # Application 생성
    application = Application.builder().token(CONFIG['telegram_bot_token']).build()
    
    # 명령어 핸들러
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("monitor", monitor_command))
    application.add_handler(CommandHandler("style", style_command))
    application.add_handler(CommandHandler("api", api_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("config", config_command))
    application.add_handler(CommandHandler("chatid", chatid_command))
    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(CommandHandler("reset", reset_command))
    
    # 콜백 핸들러
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # 일반 메시지 핸들러 (AI 대화)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_command))
    
    # 초기화
    application.post_init = post_init
    
    # 봇 실행
    print("🔄 봇 시작 중...\n")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
