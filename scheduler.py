from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz

class MonitoringScheduler:
    """모니터링 스케줄러 (YouTube + Website만)"""
    
    def __init__(self, config, bot):
        self.config = config
        self.bot = bot
        self.scheduler = None
        
        print("\n" + "="*60)
        print("🔧 수집기 초기화 중...")
        print("="*60 + "\n")
        
        # YouTube 수집기
        youtube_api_key = config.get('youtube_api_key')
        if youtube_api_key:
            from collectors.youtube_channel_collector import YouTubeChannelCollector
            self.youtube_collector = YouTubeChannelCollector(youtube_api_key, config)
            print("✅ YouTube 수집기 초기화 완료")
        else:
            self.youtube_collector = None
            print("⚠️  YouTube 수집기 비활성화")
        
        # Website 수집기
        from collectors.website_collector import WebsiteCollector
        self.website_collector = WebsiteCollector(config)
        print("✅ Website 수집기 초기화 완료")
        
        # AI 분석기
        from analyzers.trend_analyzer import TrendAnalyzer
        
        provider = config.get('llm_provider', 'deepseek')
        report_style = config.get('report_style', 'professional')
        
        api_key = {
            'deepseek': config.get('deepseek_api_key'),
            'groq': config.get('groq_api_key'),
            'gemini': config.get('gemini_api_key'),
            'claude': config.get('anthropic_api_key'),
        }.get(provider)
        
        self.analyzer = TrendAnalyzer(api_key, provider=provider, report_style=report_style)
        print("✅ AI 분석기 초기화 완료")
        
        # 리포터
        from reporters.report_generator import ReportGenerator
        self.reporter = ReportGenerator(bot)
        print("✅ 리포터 초기화 완료")
    
    def start_scheduler(self):
        """스케줄러 시작"""
        if not self.config.get('schedule', {}).get('enabled', True):
            return
        
        import asyncio
        
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            print("⚠️  이벤트 루프 대기 중")
            return
        
        kst = pytz.timezone('Asia/Seoul')
        self.scheduler = AsyncIOScheduler(timezone=kst)
        
        daily_time = self.config.get('schedule', {}).get('daily_report_time', '08:00')
        hour, minute = daily_time.split(':')
        
        self.scheduler.add_job(
            self.run_monitoring_task,
            CronTrigger(hour=int(hour), minute=int(minute), timezone=kst),
            id='daily_report'
        )
        
        self.scheduler.start()
        
        now_kst = datetime.now(kst)
        next_run = self.scheduler.get_job('daily_report').next_run_time
        
        print(f"\n⏰ 스케줄러 시작")
        print(f"   • 현재: {now_kst.strftime('%Y-%m-%d %H:%M:%S')} (KST)")
        print(f"   • 일일: 매일 {daily_time}")
        print(f"   • 다음: {next_run.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    async def run_monitoring_task(self):
        """모니터링 실행"""
        print("\n" + "="*60)
        print("🚀 모니터링 시작")
        print("="*60 + "\n")
        
        try:
            # === 1. YouTube 수집 ===
            youtube_data = []
            if self.youtube_collector:
                print("📺 YouTube 수집 중...\n")
                youtube_by_category = await self.youtube_collector.collect_all_channels()
                
                for category, videos in (youtube_by_category or {}).items():
                    if videos:
                        youtube_data.extend(videos)
                
                print(f"   📊 YouTube 총 {len(youtube_data)}개\n")
            
            # === 2. Website 수집 ===
            print("📡 Website 수집 중...")
            website_data = await self.website_collector.collect() or []
            
            # === 3. 시장 데이터 수집 (AI 분석 전에!) ===
            print("📊 시장 데이터 수집 중...")
            from collectors.market_data_collector import MarketDataCollector
            market_collector = MarketDataCollector(self.config)
            market_data = market_collector.get_all_market_data()
            print("✅ 시장 데이터 수집 완료\n")
            
            # === 4. AI 분석 (시장 데이터 포함) ===
            print("🤖 AI 분석 중...")
            analysis = self.analyzer.analyze_data(youtube_data, website_data, market_data)
            print("✅ AI 분석 완료\n")
            
            # === 5. 리포트 저장 (챗봇용) ===
            try:
                with open('/tmp/latest_report.txt', 'w', encoding='utf-8') as f:
                    f.write(f"수집 날짜: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                    f.write(f"YouTube: {len(youtube_data)}개\n")
                    f.write(f"Website: {len(website_data)}개\n\n")
                    
                    # 시장 데이터 포함
                    if market_data:
                        f.write("=== 실시간 시장 데이터 ===\n\n")
                        for symbol, data in market_data.items():
                            price = data.get('price', 0)
                            change_pct = data.get('change_percent', 0)
                            f.write(f"{symbol}: ${price:,.2f} ({change_pct:+.2f}%)\n")
                        f.write("\n")
                    
                    f.write("=== AI 분석 결과 ===\n\n")
                    f.write(analysis)
                
                print("💾 리포트 저장 완료 (/tmp/latest_report.txt)\n")
            except Exception as e:
                print(f"   ⚠️  리포트 저장 실패: {str(e)}\n")
            
            # === 6. 리포트 발송 ===
            recipients = self.config.get('report_recipients', [])
            
            print(f"📤 리포트 발송 ({len(recipients)}명)...")
            
            for chat_id in recipients:
                try:
                    await self.reporter.send_report(
                        chat_id,
                        analysis,
                        {
                            'youtube_count': len(youtube_data),
                            'website_count': len(website_data)
                        },
                        market_data=market_data,
                        youtube_data=youtube_data,
                        website_data=website_data
                    )
                    print(f"   ✅ 발송: {chat_id}")
                except Exception as e:
                    print(f"   ❌ 실패 ({chat_id}): {str(e)}")
            
            print("\n✅ 완료!")
            
        except Exception as e:
            print(f"\n❌ 실패: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*60 + "\n")
