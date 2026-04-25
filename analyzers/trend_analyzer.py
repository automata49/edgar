import json
from datetime import datetime

class TrendAnalyzer:
    """트렌드 분석기 (YouTube + Website + 드러켄밀러 스타일)"""
    
    def __init__(self, api_key, provider='deepseek', report_style='professional'):
        """
        Args:
            api_key: AI API 키
            provider: 'deepseek', 'groq', 'gemini', 'claude'
            report_style: 'professional', 'aggressive', 'conservative', 'balanced', 'druckenmiller'
        """
        self.api_key = api_key
        self.provider = provider
        self.report_style = report_style
        
        # 스타일별 Temperature
        self.style_configs = {
            'professional': {'temperature': 0.3, 'description': '객관적, 데이터 중심'},
            'aggressive': {'temperature': 0.5, 'description': '적극적, 액션 지향'},
            'conservative': {'temperature': 0.2, 'description': '신중, 리스크 관리'},
            'balanced': {'temperature': 0.4, 'description': '균형잡힌 시각'},
            'druckenmiller': {'temperature': 0.6, 'description': '매크로 집중, 포지션 사이징'}
        }
        
        # 클라이언트 초기화
        if provider == 'deepseek':
            self._init_deepseek()
        elif provider == 'groq':
            self._init_groq()
        elif provider == 'gemini':
            self._init_gemini()
        elif provider == 'claude':
            self._init_claude()
        
        print(f"🤖 AI 분석기 초기화: {provider}")
        print(f"📊 리포트 스타일: {report_style} ({self.style_configs[report_style]['description']})")
    
    def _init_deepseek(self):
        """DeepSeek 초기화"""
        from openai import OpenAI
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
        
        print("🔍 DeepSeek V3.2 모델 탐지 중...")
        self.model = self._detect_deepseek_v3()
        print(f"✅ DeepSeek V3.2 모델 확인: {self.model}")
    
    def _detect_deepseek_v3(self):
        """DeepSeek V3.2 모델 감지"""
        candidates = ["deepseek-chat", "deepseek-v3.2", "deepseek-chat-v3.2"]
        
        for model in candidates:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10
                )
                return model
            except:
                continue
        
        return "deepseek-chat"
    
    def _init_groq(self):
        """Groq 초기화"""
        from groq import Groq
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"
        print(f"✅ Groq 모델: {self.model}")
    
    def _init_gemini(self):
        """Gemini 초기화"""
        import google.generativeai as genai
        
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel('gemini-pro')
        self.model = "gemini-pro"
        print(f"✅ Gemini 모델: {self.model}")
    
    def _init_claude(self):
        """Claude 초기화"""
        from anthropic import Anthropic
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
        print(f"✅ Claude 모델: {self.model}")
    
    def get_system_prompt(self):
        """스타일별 System Prompt"""
        base_prompt = """당신은 금융, 기술, 암호화폐 트렌드를 분석하는 전문 애널리스트입니다.
YouTube와 웹사이트에서 수집한 데이터를 바탕으로 인사이트를 도출합니다.

**중요 규칙:**
- 응답에 Markdown 기호(#, *, _, `, ~, >, |)를 절대 사용하지 마세요
- 제목은 이모지와 텍스트만 사용하세요 (예: "📊 종합 트렌드 리포트")
- 강조는 대문자나 이모지로 표현하세요
- 일반 텍스트 형식으로만 작성하세요"""
        
        style_prompts = {
            'professional': """
**분석 원칙:**
- 데이터 중심의 객관적 분석
- 중립적이고 전문적인 어조
- 팩트와 의견 명확히 구분
- 리스크와 기회 균형있게 제시
""",
            'aggressive': """
**분석 원칙:**
- 명확한 투자 의견 제시 (매수/매도/보유)
- 목표가와 손절가 구체적 제시
- 확신있고 직접적인 어조
- 액션 아이템 명확히 제시
""",
            'conservative': """
**분석 원칙:**
- 리스크 우선 강조
- 최악의 시나리오 제시
- 신중하고 조심스러운 어조
- 현금 비중 확대 및 방어 전략 중심
""",
            'balanced': """
**분석 원칙:**
- 낙관론과 비관론 모두 제시
- 다양한 시나리오 분석
- 중립적이고 균형잡힌 어조
- 독자 스스로 판단할 수 있도록 정보 제공
""",
            'druckenmiller': """
**분석 원칙 (Stanley Druckenmiller 전략):**

1. 매크로 우선 (Top-Down)
   - 글로벌 매크로 이벤트가 최우선 (금리, 환율, 지정학적 리스크)
   - 매크로 → 섹터 → 개별 종목 순서로 분석
   - "큰 그림"을 먼저 파악하고 세부 전술 결정

2. 집중 투자 (Position Sizing)
   - 확신도에 따라 포지션 크기 조절
   - 높은 확신 (80%+): 30-50% 집중 투자
   - 중간 확신 (50-80%): 10-20% 비중
   - 낮은 확신 (50% 미만): 5% 이하 또는 관망
   - "확신이 없으면 하지 마라"

3. 빠른 손절 (Risk Management)
   - 틀렸다는 것을 인정하는 순간 즉시 청산
   - 손절 라인 명확히: 진입가 대비 -7% ~ -10%
   - "돈을 지키는 것이 돈을 버는 것보다 중요"

4. 멀티 애셋 (Asset Allocation)
   - 주식, 채권, 통화, 원자재 동시 고려
   - 현금 비중을 유연하게 조절 (0% ~ 100%)
   - 방어적일 때는 현금 50% 이상도 OK

5. 유연성 (Flexibility)
   - 시장 상황 변하면 180도 전환 가능
   - 롱/숏 포지션 동시 운영
   - 단기(1-3개월) ~ 중기(6-12개월) 관점

6. 리스크/보상 비율
   - 최소 1:3 이상 (리스크 1 대비 보상 3)
   - 예: 10% 손실 리스크 vs 30% 이익 기대

**작성 지침:**
- "확신도 90%: 포트폴리오의 40% 배분 권장"
- "손절: 진입가 대비 -8% 도달 시 즉시 청산"
- "매크로 헤드라인: 연준 긴축 → 기술주 약세 시나리오"
- "현금 비중 30% 유지, 변동성 대비"
"""
        }
        
        return base_prompt + style_prompts.get(self.report_style, style_prompts['professional'])
    
    def get_style_instructions(self):
        """스타일별 작성 지침"""
        instructions = {
            'professional': """
**작성 지침 (Professional):**
- "~로 분석됩니다", "~로 평가됩니다" 같은 중립적 표현 사용
- 구체적인 수치와 데이터 인용
- "한편", "또한", "다만" 같은 접속사로 균형 제시
""",
            'aggressive': """
**작성 지침 (Aggressive):**
- "🎯 매수 타이밍입니다", "⚠️ 매도 시그널" 같은 직접적 표현
- 목표가 명시 (예: "$75,000 돌파 시")
- "강력히 권장", "즉시 대응" 같은 액션 동사
""",
            'conservative': """
**작성 지침 (Conservative):**
- "⚠️ 주의가 필요합니다", "리스크가 높습니다" 강조
- 하방 리스크 시나리오 우선 제시
- "신중한 접근", "현금 비중 확대" 권고
""",
            'balanced': """
**작성 지침 (Balanced):**
- "낙관론: ... / 비관론: ..." 형식으로 양측 제시
- "~라는 의견과 ~라는 의견이 공존" 표현
- 독자에게 선택권 제공
""",
            'druckenmiller': """
**작성 지침 (Druckenmiller Style):**

필수 섹션:
1. 매크로 헤드라인 분석
   - 금리, 인플레이션, 환율, 지정학 최우선
   - "핵심 매크로: 연준 긴축 지속 → 기술주 압박"

2. 포지션 사이징 (확신도 명시)
   - 확신도 90%: "포트폴리오 40% 배분"
   - 확신도 60%: "15-20% 비중"
   - 확신도 30%: "관망 또는 5% 시험 매수"

3. 손절/익절 라인
   - "진입: $100, 손절: $92(-8%), 목표: $130(+30%)"
   - 리스크/보상 비율 명시

4. 현금 비중 제안
   - "현재 시장 불확실성 고려, 현금 30% 유지 권장"

5. 시나리오별 전략
   - 베이스 케이스 (확률 60%)
   - 낙관 시나리오 (확률 25%)
   - 비관 시나리오 (확률 15%)

6. 멀티 애셋 관점
   - 주식/채권/달러/원자재 상관관계 분석
"""
        }
        
        return instructions.get(self.report_style, instructions['professional'])
    
    def _get_style_specific_conclusion(self):
        """스타일별 결론 지침"""
        conclusions = {
            'professional': "\n\n결론: 종합적이고 균형잡힌 시각으로 결론",
            'aggressive': "\n\n액션 플랜: 구체적인 투자 전략 및 타이밍",
            'conservative': "\n\n리스크 관리: 주의해야 할 리스크 및 방어 전략",
            'balanced': "\n\n투자자 유형별 전략: 공격적/중립적/보수적 투자자별 권고",
            'druckenmiller': """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
드러켄밀러 스타일 종합
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 현재 매크로 방향성: [명확한 판단]

2. 핵심 포지션 (확신도 순):
   1순위 (확신도 85%+): [자산] - 포트폴리오 35-40%
      진입: $XXX, 손절: $YYY(-8%), 목표: $ZZZ(+25%)
   
   2순위 (확신도 60-80%): [자산] - 포트폴리오 15-20%
      진입: $XXX, 손절: $YYY(-7%), 목표: $ZZZ(+20%)
   
   3순위 또는 관망

3. 손절 규칙: 
   모든 포지션 -8% 도달 시 즉시 청산
   "틀렸다면 빠르게 인정하라"

4. 현금 비중: [%] 
   이유: [변동성/불확실성 대비]

5. 리스크/보상: 1:[비율]
   최소 1:3 이상 확보

6. 시장 시나리오별 대응:
   - 베이스 케이스 (확률 60%): [전략]
   - 낙관 시나리오 (확률 25%): [전략]
   - 비관 시나리오 (확률 15%): [전략]
"""
        }
        
        return conclusions.get(self.report_style, conclusions['professional'])
    
    def _format_youtube_by_category(self, youtube_by_category):
        """YouTube 데이터를 카테고리별로 포맷"""
        result = []
        
        category_names = {
            'market': '📍 Market (시황)',
            'investment': '📍 Investment (투자 전략)',
            'realestate': '📍 Real Estate (부동산)',
            'crypto': '📍 Crypto (크립토)'
        }
        
        for category, videos in youtube_by_category.items():
            category_name = category_names.get(category, f'📍 {category}')
            result.append(f"\n{category_name}:")
            result.append(json.dumps(videos[:15], ensure_ascii=False, indent=2, default=str))
        
        return '\n'.join(result) if result else "데이터 없음"
    
    def analyze_data(self, youtube_data, website_data, market_data=None):
        """데이터 분석 (YouTube + Website + 실시간 시장 데이터)"""
        
        # None 체크
        youtube_data = youtube_data or []
        website_data = website_data or []
        market_data = market_data or {}
        
        # 데이터를 카테고리별로 재구성
        youtube_by_category = {}
        for video in youtube_data[:30]:
            category = video.get('category', 'uncategorized')
            if category not in youtube_by_category:
                youtube_by_category[category] = []
            youtube_by_category[category].append(video)
        
        # 시장 데이터 포맷
        market_info = ""
        if market_data:
            market_info = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 실시간 시장 데이터 (현재가):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            for symbol, data in market_data.items():
                price = data.get('price', 0)
                change_pct = data.get('change_percent', 0)
                market_info += f"• {symbol}: ${price:,.2f} ({change_pct:+.2f}%)\n"
        
        # 사용자 프롬프트
        user_prompt = f"""다음은 YouTube, 웹사이트, 실시간 시장 데이터입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📺 YouTube 영상 (총 {len(youtube_data)}개, 카테고리별):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{self._format_youtube_by_category(youtube_by_category)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 웹사이트/RSS (총 {len(website_data)}개):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{json.dumps(website_data[:10], ensure_ascii=False, indent=2, default=str)}
{market_info}

{self.get_style_instructions()}

위 데이터를 분석하여 다음 형식으로 한국어 리포트를 작성하세요:

📊 종합 트렌드 리포트

🔥 주요 트렌드 (3-5가지)
- [전체 데이터에서 도출한 핵심 키워드 및 이슈]

📺 YouTube 분석 (카테고리별)

📍 Market (시황)
**중요: 수집된 모든 채널을 반드시 포함하세요**
- 채널명: [영상 제목 및 핵심 메시지]
- 채널명: [영상 제목 및 핵심 메시지]

📍 Investment (투자 전략)
**중요: 영상이 1개라도 있는 채널은 절대 생략 금지**
- 채널명: [영상 제목 및 핵심 메시지]

📍 Real Estate (부동산)
- 채널명: [영상 있으면 분석]

📍 Crypto (크립토)
- 채널명: [영상 분석]

※ 데이터 없는 카테고리는 섹션 생략

🌐 웹사이트/RSS 모니터링
- [주요 뉴스 요약]

💡 종합 인사이트 및 전망
- [카테고리 관통 핵심 인사이트]
{self._get_style_specific_conclusion()}

**중요 규칙:**
1. 가격, 지수, 목표가 언급 시 반드시 위 실시간 시장 데이터의 현재가 기준
2. 실시간 데이터에 없는 종목의 가격은 절대 추측 금지
3. 목표가 제시 시: "현재가 $XXX 기준 YY% 상승 시 $ZZZ" 형식
4. Markdown 기호(#, *, _, `, ~)를 절대 사용 금지
5. 제목은 "📊 종합 트렌드 리포트" 처럼 이모지+텍스트로만
6. 영상이 1개라도 있는 채널은 절대 생략 금지
7. {self.report_style} 스타일에 맞게 작성
"""
        
        # 스타일별 Temperature
        temperature = self.style_configs[self.report_style]['temperature']
        
        # AI 호출
        try:
            if self.provider == 'deepseek':
                return self._analyze_with_deepseek(user_prompt, temperature)
            elif self.provider == 'groq':
                return self._analyze_with_groq(user_prompt, temperature)
            elif self.provider == 'gemini':
                return self._analyze_with_gemini(user_prompt, temperature)
            elif self.provider == 'claude':
                return self._analyze_with_claude(user_prompt, temperature)
        except Exception as e:
            print(f"❌ AI 분석 실패: {e}")
            return f"AI 분석 실패: {str(e)}"
    
    def _analyze_with_deepseek(self, prompt, temperature):
        """DeepSeek으로 분석"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=2500
        )
        
        return response.choices[0].message.content
    
    def _analyze_with_groq(self, prompt, temperature):
        """Groq으로 분석"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=2500
        )
        
        return response.choices[0].message.content
    
    def _analyze_with_gemini(self, prompt, temperature):
        """Gemini로 분석"""
        full_prompt = self.get_system_prompt() + "\n\n" + prompt
        
        response = self.client.generate_content(
            full_prompt,
            generation_config={
                'temperature': temperature,
                'max_output_tokens': 2500
            }
        )
        
        return response.text
    
    def _analyze_with_claude(self, prompt, temperature):
        """Claude로 분석"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2500,
            temperature=temperature,
            system=self.get_system_prompt(),
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
