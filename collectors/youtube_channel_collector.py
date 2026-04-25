from googleapiclient.discovery import build
from datetime import datetime, timedelta

class YouTubeChannelCollector:
    """YouTube 채널 수집 + 자막"""
    
    def __init__(self, api_key, config):
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.config = config
        self.channels_config = config.get('youtube_channels', {})
        self.timeframe_hours = config.get('collection_timeframes', {}).get('youtube', 24)
        self.debug = True
        
        # 자막 추출기
        from collectors.youtube_transcript_extractor import YouTubeTranscriptExtractor
        self.transcript_extractor = YouTubeTranscriptExtractor()
    
    def extract_channel_id(self, url):
        """URL에서 채널 ID 추출"""
        if '/@' in url:
            username = url.split('/@')[1].split('/')[0].split('?')[0]
            return self.get_channel_id_by_username(username)
        
        if '/channel/' in url:
            return url.split('/channel/')[1].split('/')[0].split('?')[0]
        
        return None
    
    def get_channel_id_by_username(self, username):
        """Username → 채널 ID"""
        try:
            request = self.youtube.search().list(
                part='snippet',
                q=username,
                type='channel',
                maxResults=1
            )
            response = request.execute()
            
            if response.get('items'):
                return response['items'][0]['snippet']['channelId']
        except:
            pass
        
        return None
    
    def get_channel_videos(self, channel_url, category, max_results=2):
        """채널 최신 영상 가져오기 (시간 제한 없음)"""
        channel_id = self.extract_channel_id(channel_url)
        
        if not channel_id:
            if self.debug:
                print(f"         ❌ 채널 ID 없음: {channel_url}")
            return []
        
        try:
            if self.debug:
                print(f"         수집: 최신 {max_results}개 영상")
            
            request = self.youtube.search().list(
                part='snippet',
                channelId=channel_id,
                type='video',
                order='date',
                # publishedAfter 제거 - 최신 영상만
                maxResults=max_results
            )
            
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                snippet = item['snippet']
                
                videos.append({
                    'video_id': video_id,
                    'title': snippet['title'],
                    'channel': snippet['channelTitle'],
                    'channel_url': channel_url,
                    'category': category,
                    'published_at': snippet['publishedAt'],
                    'description': snippet.get('description', '')[:200],
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                })
            
            return videos
        except Exception as e:
            print(f"      ⚠️  영상 수집 실패: {str(e)[:80]}")
            return []
    
    async def collect_all_channels(self):
        """모든 채널 수집 + 자막"""
        all_videos = {}
        
        for category, channel_urls in self.channels_config.items():
            print(f"   📍 {category} 채널 ({len(channel_urls)}개):")
            category_videos = []
            
            for url in channel_urls:
                channel_name = url.split('/@')[1] if '/@' in url else url.split('/')[-1]
                videos = self.get_channel_videos(url, category, max_results=2)
                category_videos.extend(videos)
                
                if videos:
                    print(f"      ✅ {channel_name}: {len(videos)}개")
                else:
                    print(f"      ⚠️  {channel_name}: 0개")
            
            # 자막 추출
            if category_videos:
                print(f"      📝 자막 추출 중...")
                category_videos = self.transcript_extractor.extract_transcripts_batch(category_videos)
                transcript_count = sum(1 for v in category_videos if v.get('has_transcript'))
                print(f"      ✅ 자막: {transcript_count}/{len(category_videos)}개")
            
            all_videos[category] = category_videos
            print()
        
        return all_videos
