from datetime import datetime

class ReportGenerator:
    """리포트 생성기 (YouTube + Website + Finviz)"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def send_report(self, chat_id, analysis, stats, market_data=None, youtube_data=None, website_data=None):
        """리포트 발송 (4개 파트로 분할)"""
        try:
            # None 체크
            stats = stats or {}
            market_data = market_data or {}
            youtube_data = youtube_data or []
            website_data = website_data or []
            
            # === Markdown 기호 제거 함수 ===
            def clean_markdown(text):
                """#, *, _, `, ~ 등 Markdown 기호 제거"""
                if not text:
                    return text
                cleaned = text
                # 모든 Markdown 기호 제거
                for char in ['#', '*', '_', '`', '~', '>', '|']:
                    cleaned = cleaned.replace(char, '')
                return cleaned
            
            # === 파트 1: 헤더 + 통계 + 시장 데이터 ===
            now = datetime.now()
            message1 = f"📊 {now.strftime('%Y-%m-%d %H:%M')} 트렌드 리포트\n"
            message1 += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            # 수집 통계
            message1 += "📈 수집 데이터 통계:\n"
            message1 += f"• YouTube: {stats.get('youtube_count', 0)}개\n"
            message1 += f"• Website/RSS: {stats.get('website_count', 0)}개\n\n"
            
            # 시장 데이터
            if market_data:
                message1 += self._format_market_data(market_data)
            
            # 파트 1 발송
            await self.bot.send_message(
                chat_id=chat_id,
                text=message1,
                disable_web_page_preview=True
            )
            
            # === 분석 내용 분할 ===
            # Markdown 제거
            clean_analysis = clean_markdown(analysis)
            
            # "액션 플랜"으로 분할
            if "액션 플랜:" in clean_analysis:
                parts = clean_analysis.split("액션 플랜:", 1)
                main_analysis = parts[0].strip()
                action_plan = "📋 액션 플랜:\n\n" + parts[1].strip()
            else:
                main_analysis = clean_analysis
                action_plan = None
            
            # === 파트 2: 주요 분석 (액션 플랜 제외) ===
            await self.bot.send_message(
                chat_id=chat_id,
                text=main_analysis,
                disable_web_page_preview=True
            )
            
            # === 파트 3: 액션 플랜 (있으면) ===
            if action_plan:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=action_plan,
                    disable_web_page_preview=True
                )
            
            # === 파트 4: 소스 링크 ===
            message_sources = "📎 출처:\n"
            
            # YouTube 소스
            if youtube_data:
                message_sources += self._format_youtube_sources(youtube_data)
            
            # Website 소스
            if website_data:
                message_sources += self._format_website_sources(website_data)
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=message_sources,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            print(f"리포트 발송 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def _format_market_data(self, market_data):
        """시장 데이터 포맷"""
        message = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += "📈 *시장 현황 (실시간)*\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # 증시
        message += "📊 *증시:*\n"
        for symbol in ['SPX', 'NASDAQ', 'DOW', 'KOSPI']:
            data = market_data.get(symbol, {})
            if data:
                price = data.get('price', 0)
                change_pct = data.get('change_percent', 0)
                emoji = '🔴' if change_pct < 0 else '🟢'
                message += f"{emoji} {symbol}: ${price:,.2f} ({change_pct:+.2f}%)\n"
        
        # 채권
        message += "\n💰 *채권/금리:*\n"
        us10y = market_data.get('US10Y', {})
        if us10y:
            price = us10y.get('price', 0)
            change_pct = us10y.get('change_percent', 0)
            emoji = '🔴' if change_pct < 0 else '🟢'
            message += f"{emoji} US 10Y: {price:.3f}% ({change_pct:+.2f}%)\n"
        
        # 원자재
        message += "\n⛽ *원자재/환율:*\n"
        for symbol in ['OIL', 'GOLD', 'DXY']:
            data = market_data.get(symbol, {})
            if data:
                price = data.get('price', 0)
                change_pct = data.get('change_percent', 0)
                emoji = '🔴' if change_pct < 0 else '🟢'
                
                if symbol == 'OIL':
                    message += f"{emoji} WTI: ${price:.2f} ({change_pct:+.2f}%)\n"
                elif symbol == 'GOLD':
                    message += f"{emoji} GOLD: ${price:,.2f} ({change_pct:+.2f}%)\n"
                elif symbol == 'DXY':
                    message += f"{emoji} DXY: {price:.2f} ({change_pct:+.2f}%)\n"
        
        # 암호화폐
        message += "\n₿ *암호화폐:*\n"
        for symbol in ['BTC', 'ETH']:
            data = market_data.get(symbol, {})
            if data:
                price = data.get('price', 0)
                change_pct = data.get('change_percent', 0)
                emoji = '🔴' if change_pct < 0 else '🟢'
                message += f"{emoji} {symbol}: ${price:,.2f} ({change_pct:+.2f}%)\n"
        
        message += "\n"
        return message
    
    def _format_youtube_sources(self, youtube_data):
        """YouTube 소스 포맷 (카테고리별)"""
        message = "\n*📺 YouTube:*\n"
        
        # 카테고리별 그룹화
        by_category = {}
        for video in youtube_data[:20]:
            category = video.get('category', 'uncategorized')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(video)
        
        category_names = {
            'market': '시황',
            'investment': '투자',
            'realestate': '부동산',
            'crypto': '크립토'
        }
        
        for category, videos in by_category.items():
            cat_name = category_names.get(category, category)
            message += f"• {cat_name}: "
            
            links = []
            for video in videos[:3]:
                title = video.get('title', 'No title')[:30]
                url = video.get('url', '')
                if url:
                    links.append(f"[{title}...]({url})")
            
            message += ", ".join(links) + "\n"
        
        return message
    
    def _format_website_sources(self, website_data):
        """Website 소스 포맷"""
        message = "\n*🌐 Website/RSS:*\n"
        
        # 소스별 그룹화
        by_source = {}
        for article in website_data[:20]:
            source = article.get('source', 'Unknown')
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(article)
        
        for source, articles in list(by_source.items())[:5]:
            message += f"• {source}: "
            
            links = []
            for article in articles[:3]:
                title = article.get('title', 'No title')[:30]
                url = article.get('url', '')
                if url:
                    links.append(f"[{title}...]({url})")
            
            message += ", ".join(links) + "\n"
        
        return message
