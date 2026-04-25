import subprocess
import json

class YouTubeTranscriptExtractor:
    """YouTube 자막 추출 (yt-dlp 사용)"""
    
    def __init__(self):
        self.debug = True
    
    def get_transcript(self, video_id):
        """yt-dlp로 자막 추출"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # 자막 다운로드 (한국어 우선)
            cmd = [
                'yt-dlp',
                '--skip-download',
                '--write-auto-sub',
                '--sub-lang', 'ko,en',
                '--sub-format', 'json3',
                '--print', '%(subtitles)s',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                if self.debug:
                    print(f"         ✅ {video_id}: 자막 추출 성공")
                return result.stdout[:3000]
            
            if self.debug:
                print(f"         ⚠️  {video_id}: 자막 없음")
            return None
            
        except Exception as e:
            if self.debug:
                print(f"         ❌ {video_id}: {str(e)[:50]}")
            return None
    
    def extract_transcripts_batch(self, videos):
        """비디오 리스트 자막 추출"""
        results = []
        
        for video in videos:
            video_id = video.get('video_id')
            if not video_id:
                results.append(video)
                continue
            
            # 자막 추출 스킵 (너무 느림)
            # transcript = self.get_transcript(video_id)
            
            # description 사용
            transcript = video.get('description', '')[:1000]
            
            video['transcript'] = transcript
            video['has_transcript'] = bool(transcript)
            results.append(video)
        
        return results
