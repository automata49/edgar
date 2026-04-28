from __future__ import annotations

import json


class TrendAnalyzer:
    """멀티 LLM 트렌드 분석기."""

    STYLES: dict[str, dict] = {
        "professional":  {"temp": 0.3, "desc": "객관적, 데이터 중심"},
        "aggressive":    {"temp": 0.5, "desc": "적극적, 액션 지향"},
        "conservative":  {"temp": 0.2, "desc": "신중, 리스크 관리"},
        "balanced":      {"temp": 0.4, "desc": "균형잡힌 시각"},
        "druckenmiller": {"temp": 0.6, "desc": "매크로 집중, 포지션 사이징"},
    }

    def __init__(self, config: dict) -> None:
        self.provider = config.get("llm_provider", "deepseek")
        self.style    = config.get("report_style", "aggressive")
        self.temp     = self.STYLES.get(self.style, self.STYLES["aggressive"])["temp"]
        self._client  = self._init_client(config)
        print(f"🤖 AI: {self.provider} / 스타일: {self.style}")

    def analyze(self, youtube_data: list, news_data: list, market_data: dict) -> str:
        prompt = self._build_prompt(youtube_data, news_data, market_data)
        return self._call(prompt)

    # ── Init ─────────────────────────────────────────────────────────────────

    def _init_client(self, config: dict):
        p = self.provider
        if p == "deepseek":
            from openai import OpenAI
            client = OpenAI(api_key=config.get("deepseek_api_key"), base_url="https://api.deepseek.com")
            self._model = "deepseek-chat"
            return client
        if p == "groq":
            from groq import Groq
            self._model = "llama-3.3-70b-versatile"
            return Groq(api_key=config.get("groq_api_key"))
        if p == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=config.get("gemini_api_key"))
            self._model = "gemini-pro"
            return genai.GenerativeModel(self._model)
        if p == "claude":
            from anthropic import Anthropic
            self._model = "claude-sonnet-4-20250514"
            return Anthropic(api_key=config.get("anthropic_api_key"))
        raise ValueError(f"Unknown provider: {p}")

    # ── Prompt ───────────────────────────────────────────────────────────────

    def _build_prompt(self, youtube_data: list, news_data: list, market_data: dict) -> str:
        style_guides = {
            "professional":  "데이터 중심의 객관적 분석. 팩트와 의견을 명확히 구분하라.",
            "aggressive":    "명확한 매수/매도/보유 의견. 목표가와 손절가를 구체적으로 제시하라.",
            "conservative":  "리스크 우선. 최악의 시나리오와 방어 전략을 중심으로 분석하라.",
            "balanced":      "강세/약세 양면을 균형있게 분석하라.",
            "druckenmiller":  "매크로 흐름 중심. 유동성, 통화정책, 섹터 로테이션을 핵심으로 분석하라.",
        }

        market_str = "\n".join(
            f"{sym}: ${d.get('price',0):,.2f} ({d.get('change_percent',0):+.2f}%)"
            for sym, d in list(market_data.items())[:20]
        ) if market_data else "데이터 없음"

        yt_str = "\n".join(
            f"[{v.get('category','')}] {v.get('title','')} - {v.get('transcript','')[:200]}"
            for v in youtube_data[:10]
        ) if youtube_data else "없음"

        news_str = "\n".join(
            f"[{a.get('source','')}] {a.get('title','')} - {a.get('summary','')[:150]}"
            for a in news_data[:15]
        ) if news_data else "없음"

        return f"""당신은 금융 전문 애널리스트입니다.

분석 스타일: {style_guides.get(self.style, '')}

중요: Markdown 기호(#, *, _, `, ~)를 절대 사용하지 마세요. 이모지와 일반 텍스트만 사용하세요.

=== 실시간 시장 데이터 ===
{market_str}

=== YouTube 콘텐츠 ===
{yt_str}

=== 뉴스/RSS ===
{news_str}

위 데이터를 바탕으로 다음 형식으로 분석하세요:

📊 종합 트렌드 분석
(시장 전반 흐름 분석)

🎯 핵심 투자 포인트
(3-5개 핵심 포인트)

⚠️ 리스크 요인
(주요 리스크)

액션 플랜:
(구체적 행동 지침 3-5개)"""

    # ── Call ─────────────────────────────────────────────────────────────────

    def _call(self, prompt: str) -> str:
        try:
            if self.provider == "gemini":
                return self._client.generate_content(prompt).text
            if self.provider == "claude":
                msg = self._client.messages.create(
                    model=self._model, max_tokens=3000,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text
            # openai-compatible (deepseek, groq)
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temp,
                max_tokens=3000,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"분석 실패: {e}"
