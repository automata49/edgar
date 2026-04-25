import feedparser
from datetime import datetime, timedelta

class WebsiteCollector:
    """RSS 피드 수집 (웹스크래핑 제거)"""
    
    def __init__(self, config):
        self.config = config
        self.rss_feeds = config.get('rss_feeds', [])
        self.timeframe_hours = config.get('collection_timeframes', {}).get('website', 24)
    
    def collect_rss(self, feed_url):
        """RSS 피드 수집"""
        try:
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                return []
            
            cutoff_time = datetime.now() - timedelta(hours=self.timeframe_hours)
            
            articles = []
            for entry in feed.entries[:20]:
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])
                
                if published and published < cutoff_time:
                    continue
                
                articles.append({
                    'title': entry.get('title', 'No title'),
                    'url': entry.get('link', ''),
                    'summary': entry.get('summary', '')[:200],
                    'published': published.isoformat() if published else None,
                    'source': feed.feed.get('title', feed_url.split('/')[2] if '/' in feed_url else feed_url),
                })
            
            return articles[:10]
        except Exception as e:
            print(f"   ⚠️  RSS 실패 ({feed_url.split('/')[2] if '/' in feed_url else feed_url}): {str(e)[:50]}")
            return []
    
    async def collect(self):
        """RSS 수집"""
        all_articles = []
        
        if not self.rss_feeds:
            print("   ⚠️  RSS 피드가 설정되지 않았습니다.")
            return []
        
        print(f"📡 RSS 피드 수집 ({len(self.rss_feeds)}개):")
        
        for feed_url in self.rss_feeds:
            articles = self.collect_rss(feed_url)
            all_articles.extend(articles)
            
            source_name = feed_url.split('/')[2] if '/' in feed_url else feed_url
            
            if articles:
                print(f"   ✅ {source_name}: {len(articles)}개")
            else:
                print(f"   ⚠️  {source_name}: 0개")
        
        # 중복 제거
        seen = set()
        unique_articles = []
        for article in all_articles:
            url = article.get('url', '')
            if url and url not in seen:
                seen.add(url)
                unique_articles.append(article)
        
        print(f"   📊 총 {len(unique_articles)}개 수집 완료\n")
        
        return unique_articles
