from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime


# ── Video-spec dataclasses (AIVideoGenerator 호환, script.py 의존성 없음) ──────

@dataclass
class _SceneSpec:
    """AIVideoGenerator가 기대하는 scene 인터페이스."""
    scene_num:    int
    label:        str
    character:    str
    dialogue:     str
    visual_note:  str
    duration:     float
    emphasis:     bool


@dataclass
class _VideoSpec:
    """AIVideoGenerator.generate() 에 전달하는 script-like 객체."""
    stock_name:       str
    format_type:      str
    hook_text:        str
    hook_subtext:     str
    first_frame:      dict
    characters:       list
    scenes:           list[_SceneSpec]
    subtitles:        list[dict]
    cta_text:         str
    hashtags:         list[str]
    title:            str
    description:      str
    full_narration:   str = ""   # TTS에서 사용
    celeb_characters: None = None


# ── Main dataclass ────────────────────────────────────────────────────────────

@dataclass
class KoreanShortScript:
    """30초 한국어 숏폼 대본."""
    stock_name:      str
    hook:            str   # A. 0~2초: 스크롤 멈추게 만드는 첫 마디
    context:         str   # B. 2~5초: 배경 설명
    value_twist:     str   # C. 5~20초: 핵심 내용 + 반전
    payoff_loop:     str   # D. 마지막 3초: 마무리 + 루프 유도
    full_narration:  str   # 전체 연속 대본 (녹음용)
    narrator_notes:  str   # 촬영/편집 힌트
    key_themes:      list[str] = field(default_factory=list)
    sentiment:       str = "중립"
    generated_at:    str = ""

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()

    # ── AIVideoGenerator 어댑터 ───────────────────────────────────────────────

    def to_video_spec(self) -> _VideoSpec:
        """
        AIVideoGenerator.generate() 에 전달할 수 있는 _VideoSpec 객체 반환.

        구조 매핑 (총 ~26초):
          Hook clip  3s  ← hook
          Scene B    3s  ← context
          Scene C   15s  ← value_twist  (emphasis=True)
          CTA clip   5s  ← payoff_loop
        """
        accent = {"긍정": "green", "부정": "red"}.get(self.sentiment, "blue")
        theme_label = self.key_themes[0] if self.key_themes else self.stock_name

        scenes = [
            _SceneSpec(
                scene_num=1,
                label="📌 배경",
                character="",
                dialogue=self.context,
                visual_note=f"k_context_{accent}",
                duration=3.0,
                emphasis=False,
            ),
            _SceneSpec(
                scene_num=2,
                label="💡 핵심",
                character="",
                dialogue=self.value_twist,
                visual_note=f"k_value_{accent}",
                duration=15.0,
                emphasis=True,
            ),
        ]

        subtitles = [
            {"time_start": 0,  "time_end": 3,  "text": self.hook},
            {"time_start": 3,  "time_end": 6,  "text": self.context},
            {"time_start": 6,  "time_end": 21, "text": self.value_twist},
            {"time_start": 21, "time_end": 26, "text": self.payoff_loop},
        ]

        return _VideoSpec(
            stock_name       = self.stock_name,
            format_type      = "korean_short",
            hook_text        = self.hook,
            hook_subtext     = " · ".join(self.key_themes[:2]),
            first_frame      = {
                "headline": f"📊 {theme_label}",
                "stat":     "",
                "color":    accent,
            },
            characters       = [],
            scenes           = scenes,
            subtitles        = subtitles,
            cta_text         = self.payoff_loop,
            hashtags         = [
                f"#{self.stock_name}", "#주식분석", "#경제공부", "#재테크", "#shorts"
            ],
            title            = f"{self.stock_name} — {theme_label} | 30초 분석",
            description      = self.full_narration[:200],
            full_narration   = self.full_narration,
        )

    def to_dict(self) -> dict:
        return {
            "stock_name":     self.stock_name,
            "hook":           self.hook,
            "context":        self.context,
            "value_twist":    self.value_twist,
            "payoff_loop":    self.payoff_loop,
            "full_narration": self.full_narration,
            "narrator_notes": self.narrator_notes,
            "key_themes":     self.key_themes,
            "sentiment":      self.sentiment,
            "generated_at":   self.generated_at,
        }


class KoreanShortScriptGenerator:
    """
    [2단계] 종목별 요약 → 30초 한국어 숏폼 대본 생성.

    대본 구조:
      A. Hook        (0~2초)   : 시청자가 멈추게 만드는 첫 마디
      B. Context     (2~5초)   : 3초 안에 배경 설명
      C. Value/Twist (5~20초)  : 핵심 내용 전달 + 반전
      D. Payoff+Loop (마지막 3초): 마무리 + 다시 보고 싶게 만들기

    언어: 고등학생 수준의 대화체 한국어
    """

    def __init__(self, config: dict) -> None:
        self.provider   = config.get("llm_provider", "deepseek")
        cfg             = config.get("korean_script", {})
        self.output_dir = cfg.get("output_dir", "data/scripts")
        self._client    = self._init_client(config)

    # ── Public API ───────────────────────────────────────────────────────────

    def generate(self, summary: dict) -> KoreanShortScript:
        """요약 dict → 30초 한국어 대본 생성 후 저장."""
        prompt = self._build_prompt(summary)
        raw    = self._call_llm(prompt)
        script = self._parse(raw, summary)
        self._save(script)
        return script

    def generate_batch(self, summaries: list[dict]) -> list[KoreanShortScript]:
        """여러 종목 요약 → 대본 일괄 생성."""
        scripts: list[KoreanShortScript] = []
        for s in summaries:
            stock = s.get("stock_name", "?")
            print(f"   🎬 {stock} 대본 생성 중...")
            scripts.append(self.generate(s))
        return scripts

    # ── Prompt ───────────────────────────────────────────────────────────────

    def _build_prompt(self, summary: dict) -> str:
        stock     = summary.get("stock_name", "")
        one_line  = summary.get("one_line", "")
        sentiment = summary.get("sentiment", "중립")
        themes    = summary.get("key_themes", [])
        details   = summary.get("theme_details", [])
        overall   = summary.get("summary", "")

        details_str = "\n".join(
            f"  [{d.get('theme', '')}] {d.get('content', '')} — {d.get('key_stat', '')} "
            f"({d.get('why_matters', '')})"
            for d in details
        )

        sentiment_emoji = {"긍정": "📈", "부정": "📉", "중립": "📊"}.get(sentiment, "📊")

        return f"""당신은 MZ세대가 즐겨보는 30초 숏폼 영상 대본 작가입니다.

## 종목: {stock} {sentiment_emoji}
## 한 줄 요약: {one_line}
## 분위기: {sentiment}
## 핵심 주제: {', '.join(themes)}
## 주제별 내용:
{details_str}
## 전체 흐름:
{overall}

---
**대본 구조 (총 30초, 약 150~180자):**

A. Hook (0~2초, 약 20자 이내)
   - 시청자가 스크롤을 멈추는 첫 마디
   - 질문, 충격 사실, 또는 강한 주장으로 시작
   - 예: "야, {stock} 지금 이거 알아?" / "{stock} 근데 왜 올랐지?"

B. Context (2~5초, 약 30자 이내)
   - 배경 설명 (3초짜리)
   - 쉬운 말로 상황 정리

C. Value / Twist (5~20초, 약 80~100자)
   - 핵심 내용 전달 (15초)
   - 숫자와 구체적 사실 포함
   - 중간에 예상 못한 반전 요소 하나 넣기

D. Payoff + Loop (마지막 3초, 약 25자 이내)
   - 내용을 마무리하는 한 방
   - 처음 Hook이랑 연결되어 다시 보고 싶게 만들기

**언어 스타일:**
- 친구한테 말하듯 자연스럽고 편하게
- 짧고 임팩트 있는 문장
- 어려운 금융 용어는 절대 그냥 쓰지 말 것 (예: "PER이 낮다" → "주가가 이익에 비해 싸다")
- 이모지 1~2개 사용 가능

아래 JSON 형식으로만 응답하세요 (마크다운 코드 블록 없이):

{{
  "hook": "A구간 대사 (20자 이내)",
  "context": "B구간 대사 (30자 이내)",
  "value_twist": "C구간 대사 (100자 이내, 핵심+반전 포함)",
  "payoff_loop": "D구간 대사 (25자 이내)",
  "full_narration": "A+B+C+D 이어붙인 전체 대본 (자연스럽게 연결, 중간에 끊기 없이)",
  "narrator_notes": "어떤 화면, 어떤 효과를 쓰면 좋은지 간단 힌트 (1~2줄)"
}}"""

    # ── LLM Call ─────────────────────────────────────────────────────────────

    def _call_llm(self, prompt: str) -> str:
        try:
            if self.provider == "claude":
                msg = self._client.messages.create(
                    model=self._model, max_tokens=800,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text
            if self.provider == "gemini":
                return self._client.generate_content(prompt).text
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=800,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f'{{"error": "{e}"}}'

    # ── Parse ────────────────────────────────────────────────────────────────

    def _parse(self, raw: str, summary: dict) -> KoreanShortScript:
        stock = summary.get("stock_name", "")
        try:
            m    = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(m.group()) if m else {}
        except Exception:
            data = {}

        if not data or "error" in data:
            return self._fallback(summary)

        return KoreanShortScript(
            stock_name     = stock,
            hook           = data.get("hook", ""),
            context        = data.get("context", ""),
            value_twist    = data.get("value_twist", ""),
            payoff_loop    = data.get("payoff_loop", ""),
            full_narration = data.get("full_narration", ""),
            narrator_notes = data.get("narrator_notes", ""),
            key_themes     = summary.get("key_themes", []),
            sentiment      = summary.get("sentiment", "중립"),
        )

    def _fallback(self, summary: dict) -> KoreanShortScript:
        stock    = summary.get("stock_name", "이 종목")
        one_line = summary.get("one_line", f"{stock} 분석")
        themes   = summary.get("key_themes", [])
        details  = summary.get("theme_details", [])
        stat     = details[0].get("key_stat", "") if details else ""

        hook        = f"야, {stock} 지금 이거 알아?"
        context     = f"증권사들이 {stock}을 분석했는데,"
        value_twist = f"{one_line} {('핵심 수치: ' + stat) if stat else ''} 근데 여기서 반전이 있어 — 시장은 아직 이 내용을 다 반영 못 했거든."
        payoff_loop = f"그래서 {stock}, 지금 봐야 해."

        return KoreanShortScript(
            stock_name     = stock,
            hook           = hook,
            context        = context,
            value_twist    = value_twist,
            payoff_loop    = payoff_loop,
            full_narration = f"{hook} {context} {value_twist} {payoff_loop}",
            narrator_notes = f"화면: {stock} 로고 → 숫자 그래프 → 강조 텍스트 → 마무리 자막",
            key_themes     = themes,
            sentiment      = summary.get("sentiment", "중립"),
        )

    # ── Save ─────────────────────────────────────────────────────────────────

    def _save(self, script: KoreanShortScript) -> None:
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            stock = re.sub(r"[^\w가-힣\-]", "_", script.stock_name)
            path  = os.path.join(self.output_dir, f"{stock}_script.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(script.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"   ⚠️  대본 저장 실패: {e}")

    # ── LLM Init ─────────────────────────────────────────────────────────────

    def _init_client(self, config: dict):
        p = self.provider
        if p == "deepseek":
            from openai import OpenAI
            self._model = "deepseek-chat"
            return OpenAI(api_key=config.get("deepseek_api_key"), base_url="https://api.deepseek.com")
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
            self._model = "claude-sonnet-4-6"
            return Anthropic(api_key=config.get("anthropic_api_key"))
        raise ValueError(f"Unknown provider: {p}")
