from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kstock_signal.analyzers.celeb_cast import CelebCharacter


# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class Character:
    name:        str   # e.g. "Chad Bull"
    role:        str   # e.g. "Overconfident retail investor"
    emoji:       str   # e.g. "🐂"
    text_color:  str = "green"  # green | red | yellow | white


@dataclass
class Scene:
    scene_num:    int
    label:        str        # "POV:" | "MEANWHILE" | "BREAKING" | "ACT I" | character name
    character:    str        # character name displayed on screen
    dialogue:     str        # what appears as main text on screen
    visual_note:  str        # renderer hint: dark|card|alert|meme|news|celeb_green|celeb_blue|…
    duration:     int = 8    # seconds
    emphasis:     bool = False


@dataclass
class ShortScript:
    stock_name:     str
    format_type:    str          # pov | news_parody | character_skit | meme_sequence | drama_twist | celeb_collab
    hook_text:      str          # first 3s big text
    hook_subtext:   str
    first_frame:    dict         # {headline, stat, color}
    characters:     list[Character]
    scenes:         list[Scene]
    subtitles:      list[dict]   # [{time_start, time_end, text}]
    cta_text:       str
    hashtags:       list[str]
    title:          str
    description:    str
    hook_type:      str = "bold_claim"
    total_duration: int = 55
    celeb_characters: list | None = None   # list[CelebCharacter] — celeb_collab 포맷 전용


# ── Format definitions ────────────────────────────────────────────────────────

FORMATS = {
    "pov": {
        "desc": "First-person POV storytelling. Viewer IS the investor experiencing the news.",
        "structure": "POV setup → escalating situation → twist/regret or triumph",
        "example_hook": "POV: You sold {stock} the day before the analyst upgrade 💀",
    },
    "news_parody": {
        "desc": "Parody of a breaking news broadcast about the stock.",
        "structure": "BREAKING banner → anchor reports → absurd expert quote → punchline",
        "example_hook": "BREAKING: {stock} analyst raises target. Retail investors: 🤑",
    },
    "character_skit": {
        "desc": "Two opposing characters (Bull vs Bear) debate the stock. Comedy through contrast.",
        "structure": "Introduce Bull claim → Bear counters → unexpected plot twist ending",
        "example_hook": "Bull: '{stock} is going to the moon 🚀' Bear: 'sir this is a wendys'",
    },
    "meme_sequence": {
        "desc": "Rapid-fire meme format. Each scene = one meme reaction to the news.",
        "structure": "Relatable setup meme → escalation meme → reality-check meme → ironic CTA",
        "example_hook": "Me reading the {stock} analyst report at 2am 🕐",
    },
    "drama_twist": {
        "desc": "Mini-drama with a shocking plot twist. Builds tension then subverts expectation.",
        "structure": "Calm setup → rising tension → plot twist reveal → dramatic reaction",
        "example_hook": "They said {stock} would crash. Then THIS happened.",
    },
    "celeb_collab": {
        "desc": (
            "Cinematic mini-drama starring two real-world CEOs/executives as AI avatars. "
            "Inspired by BTS SWIM MV — atmospheric, story-driven, emotionally charged. "
            "The deal/news from the analyst report becomes the plot of the drama."
        ),
        "structure": (
            "ACT I SETTING (establishing location/mood) → "
            "ACT I INTRO (Character A reacts to news) → "
            "ACT II DIALOGUE (A delivers key deal line to B) → "
            "ACT II RESPONSE (B responds with a twist) → "
            "ACT III REVEAL (unexpected consequence/irony) → "
            "CTA (audience hook)"
        ),
        "example_hook": "The deal that could change everything 🌊",
    },
}

# Character archetypes pool
CHARACTER_POOL = [
    {"name": "Chad Bull",      "role": "Overconfident retail investor who bought the dip",     "emoji": "🐂", "text_color": "green"},
    {"name": "Doomer Bear",    "role": "Perpetually bearish analyst who's always wrong",        "emoji": "🐻", "text_color": "red"},
    {"name": "Wall St. Suit",  "role": "Smug investment banker reading the analyst report",     "emoji": "🕴️", "text_color": "yellow"},
    {"name": "Retail Karen",   "role": "Emotional retail investor panic-buying or selling",     "emoji": "😤", "text_color": "white"},
    {"name": "Crypto Bro",     "role": "Person comparing everything to Bitcoin",                "emoji": "🪙", "text_color": "yellow"},
    {"name": "The Analyst",    "role": "Overly serious analyst delivering absurd price targets","emoji": "📊", "text_color": "white"},
    {"name": "News Anchor",    "role": "Dramatic TV anchor sensationalizing stock moves",       "emoji": "📺", "text_color": "white"},
    {"name": "Boomer Investor","role": "Old-school investor confused by modern markets",        "emoji": "👴", "text_color": "gray"},
]


class ScriptGenerator:
    """
    PDF 리포트 + 트렌드 패턴 → 엔터테인먼트 숏폼 스크립트 생성.

    철학: 정보 전달 X → 스토리 + 등장인물 + 패러디 + 오락
    포맷: pov / news_parody / character_skit / meme_sequence / drama_twist
    """

    def __init__(self, config: dict) -> None:
        self.provider = config.get("llm_provider", "deepseek")
        self._client  = self._init_client(config)
        self._model:  str = getattr(self, "_model", "")

    def generate(
        self,
        report: dict,
        trend_patterns: list[dict],
        market_data: dict | None = None,
    ) -> ShortScript:
        format_type = self._pick_format(trend_patterns)
        prompt      = self._build_prompt(report, trend_patterns, format_type, market_data)
        raw         = self._call_llm(prompt)
        return self._parse_response(raw, report, format_type)

    # ── Format Selection ─────────────────────────────────────────────────────

    def _pick_format(self, patterns: list[dict]) -> str:
        """engagement 데이터 기반 최적 포맷 선택. 없으면 랜덤."""
        if not patterns:
            return random.choice(list(FORMATS.keys()))
        # hook_type → format 매핑
        mapping = {
            "question":   "pov",
            "shock_stat": "news_parody",
            "bold_claim": "drama_twist",
            "listicle":   "meme_sequence",
        }
        scores: dict[str, float] = {}
        for p in patterns:
            ht  = p.get("hook_type", "bold_claim")
            fmt = mapping.get(ht, "character_skit")
            scores[fmt] = scores.get(fmt, 0) + p.get("engagement_score", 0)
        return max(scores, key=scores.get)

    # ── Prompt ───────────────────────────────────────────────────────────────

    def _build_prompt(
        self,
        report: dict,
        patterns: list[dict],
        format_type: str,
        market_data: dict | None,
    ) -> str:
        stock  = report.get("stock_name", "the stock")
        title  = report.get("title", "")
        text   = report.get("text", "")[:2500]
        nums   = report.get("key_numbers", [])
        target = report.get("target_price", "")
        num_str = ", ".join(nums) if nums else "N/A"

        fmt        = FORMATS[format_type]
        char_list  = "\n".join(
            f'  {c["emoji"]} {c["name"]}: {c["role"]}'
            for c in CHARACTER_POOL[:6]
        )
        top_hooks  = [p.get("hook_text", "") for p in patterns[:3] if p.get("hook_text")]
        trend_str  = "\n".join(f"  - {h}" for h in top_hooks) or "  - none"

        return f"""You are a viral short-form video writer specializing in ENTERTAINMENT, PARODY, and COMEDY about finance.
Your job is NOT to educate — it is to ENTERTAIN. Think SNL sketch meets Wall Street Bets.
ALL text must be in English. Be witty, punchy, and culturally current.

## Stock: {stock}
## Analyst report headline: {title}
## Key figures: {num_str}  |  Target price: {target}
## Report excerpt (Korean — use facts for comedy material, don't translate directly):
{text[:1500]}

## Format to use: {format_type.upper()}
## Format description: {fmt["desc"]}
## Story structure: {fmt["structure"]}
## Example hook style: {fmt["example_hook"].format(stock=stock)}

## Available characters (pick 2-3 that fit the story):
{char_list}

## Trending hook styles for reference:
{trend_str}

---
Write a SHORT-FORM VIDEO SCRIPT. Rules:
- Hook (first 3s) must be IMPOSSIBLE to scroll past — shocking, funny, or deeply relatable
- Each scene is a punchy beat, max 2 sentences
- Build to a comedy twist or ironic punchline at the end
- Reference real pop culture, memes, or current events where it fits
- Characters should have distinct voices and react to each other

Respond with ONLY valid JSON:

{{
  "format_type": "{format_type}",
  "hook_text": "First 3-second big screen text — funny/shocking, max 65 chars",
  "hook_subtext": "Small ironic subtitle under hook, max 45 chars",
  "first_frame": {{
    "headline": "Big label on screen (e.g. 'BREAKING', 'POV:', 'DAY 1'), max 15 chars",
    "stat": "Key number with ironic framing (e.g. '+34% 🚀' or '-12% 💀')",
    "color": "green or red"
  }},
  "characters": [
    {{"name": "Character Name", "role": "one-line role", "emoji": "emoji", "text_color": "green|red|yellow|white"}}
  ],
  "scenes": [
    {{
      "scene_num": 1,
      "label": "Scene label shown on screen (POV: / MEANWHILE / BREAKING / character name)",
      "character": "Speaking character name",
      "dialogue": "What appears on screen — punchy, 1-2 sentences, max 90 chars",
      "visual_note": "bg hint: dark|card|alert|meme|news",
      "duration": 8,
      "emphasis": false
    }}
  ],
  "subtitles": [
    {{"time_start": 0,  "time_end": 3,  "text": "Hook subtitle"}},
    {{"time_start": 3,  "time_end": 10, "text": "Scene 1"}},
    {{"time_start": 10, "time_end": 20, "text": "Scene 2"}},
    {{"time_start": 20, "time_end": 30, "text": "Scene 3"}},
    {{"time_start": 30, "time_end": 42, "text": "Scene 4"}},
    {{"time_start": 45, "time_end": 55, "text": "CTA"}}
  ],
  "cta_text": "Witty CTA that fits the story tone",
  "hashtags": ["#stocks", "#{stock}", "#wallstreetbets", "#investing", "#shorts"],
  "title": "Clickbait-but-honest YouTube title, max 80 chars",
  "description": "Short punchy description with key figures, max 200 chars"
}}"""

    # ── LLM Call ─────────────────────────────────────────────────────────────

    def _call_llm(self, prompt: str) -> str:
        try:
            if self.provider == "claude":
                msg = self._client.messages.create(
                    model=self._model, max_tokens=2500,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text
            if self.provider == "gemini":
                return self._client.generate_content(prompt).text
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,  # 창의성 높임
                max_tokens=2500,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f'{{"error": "{e}"}}'

    # ── Parse ─────────────────────────────────────────────────────────────────

    def _parse_response(self, raw: str, report: dict, format_type: str) -> ShortScript:
        stock = report.get("stock_name", "stock")
        try:
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(json_match.group()) if json_match else {}
        except Exception:
            data = {}

        if not data or "error" in data:
            return self._fallback_script(report, format_type)

        characters = [
            Character(
                name       = c.get("name", ""),
                role       = c.get("role", ""),
                emoji      = c.get("emoji", ""),
                text_color = c.get("text_color", "white"),
            )
            for c in data.get("characters", [])
        ]

        scenes = [
            Scene(
                scene_num   = s.get("scene_num", i + 1),
                label       = s.get("label", ""),
                character   = s.get("character", ""),
                dialogue    = s.get("dialogue", ""),
                visual_note = s.get("visual_note", "dark"),
                duration    = s.get("duration", 8),
                emphasis    = s.get("emphasis", False),
            )
            for i, s in enumerate(data.get("scenes", []))
        ]

        return ShortScript(
            stock_name   = stock,
            format_type  = data.get("format_type", format_type),
            hook_text    = data.get("hook_text", f"Something wild happened with {stock}"),
            hook_subtext = data.get("hook_subtext", ""),
            first_frame  = data.get("first_frame", {"headline": "BREAKING", "stat": "", "color": "green"}),
            characters   = characters,
            scenes       = scenes,
            subtitles    = data.get("subtitles", []),
            cta_text     = data.get("cta_text", "Follow for the chaos 🔔"),
            hashtags     = data.get("hashtags", [f"#{stock}", "#stocks", "#shorts"]),
            title        = data.get("title", f"{stock} — you won't believe this #shorts"),
            description  = data.get("description", ""),
            hook_type    = format_type,
        )

    def _fallback_script(self, report: dict, format_type: str) -> ShortScript:
        stock = report.get("stock_name", "the stock")
        nums  = report.get("key_numbers", [])
        stat  = (nums[0] + " 🚀") if nums else "?!"

        fmt      = FORMATS.get(format_type, FORMATS["news_parody"])
        hook_txt = fmt["example_hook"].format(stock=stock, stat=stat, target=report.get("target_price", ""))

        return ShortScript(
            stock_name   = stock,
            format_type  = format_type,
            hook_text    = hook_txt[:65],
            hook_subtext = "This is not financial advice 💀",
            first_frame  = {"headline": "BREAKING", "stat": stat, "color": "green"},
            characters   = [Character(**{k: v for k, v in CHARACTER_POOL[0].items()})],
            scenes       = [
                Scene(1, "BREAKING", "The Analyst", f"Analyst upgrades {stock}. Retail investors: 🤑", "news", 10, True),
                Scene(2, "MEANWHILE", "Chad Bull",   f"Chad who bought the dip: 'I knew it all along'", "card", 10, False),
                Scene(3, "REALITY",   "Doomer Bear", f"Doomer Bear: 'It's a dead cat bounce. Trust me bro'", "alert", 10, False),
            ],
            subtitles    = [
                {"time_start": 0,  "time_end": 3,  "text": hook_txt[:65]},
                {"time_start": 3,  "time_end": 13, "text": f"Analyst upgrades {stock}"},
                {"time_start": 13, "time_end": 23, "text": "Chad Bull enters the chat"},
                {"time_start": 23, "time_end": 33, "text": "Doomer Bear has entered the chat"},
                {"time_start": 45, "time_end": 55, "text": "Follow for the chaos 🔔"},
            ],
            cta_text     = "Follow for the chaos 🔔",
            hashtags     = [f"#{stock}", "#stocks", "#wallstreetbets", "#shorts"],
            title        = f"{stock} just did WHAT?! 😱 #shorts",
            description  = f"The {stock} saga continues. {', '.join(nums[:2])}",
            hook_type    = format_type,
        )

    # ── Celeb Collab Generation ───────────────────────────────────────────────

    def generate_celeb(
        self,
        report: dict,
        celeb_chars: list,          # list[CelebCharacter]
        trend_patterns: list[dict] | None = None,
        market_data: dict | None = None,
    ) -> ShortScript:
        """
        실존 CEO 2명을 AI 아바타로 등장시키는 cinematic 숏폼 스크립트 생성.

        - BTS SWIM MV 스타일: 분위기 있는 배경 + 감정선 있는 대화
        - 리포트의 계약/뉴스 내용을 두 CEO의 대화로 재구성
        - visual_note 에 "celeb_{color}" 형태로 씬 배경 힌트 전달
        """
        prompt = self._build_celeb_prompt(report, celeb_chars, market_data)
        raw    = self._call_llm(prompt)
        return self._parse_celeb_response(raw, report, celeb_chars)

    def _build_celeb_prompt(
        self,
        report: dict,
        celeb_chars: list,
        market_data: dict | None,
    ) -> str:
        stock   = report.get("stock_name", "the stock")
        title   = report.get("title", "")
        text    = report.get("text", "")[:2000]
        nums    = report.get("key_numbers", [])
        target  = report.get("target_price", "")
        num_str = ", ".join(nums) if nums else "N/A"

        chars = celeb_chars[:2]
        char_a = chars[0] if len(chars) > 0 else None
        char_b = chars[1] if len(chars) > 1 else None

        char_a_str = (
            f'{char_a.emoji} {char_a.name} ({char_a.role}, {char_a.nationality})'
            if char_a else "Character A"
        )
        char_b_str = (
            f'{char_b.emoji} {char_b.name} ({char_b.role}, {char_b.nationality})'
            if char_b else "Character B"
        )

        market_str = ""
        if market_data and stock in market_data:
            md = market_data[stock]
            market_str = f"Current price: ${md.get('price', 0):,.2f} ({md.get('change_percent', 0):+.2f}%)"

        return f"""You are a cinematic short-form video scriptwriter.
Create a 60-second STORY-DRIVEN short video script starring two real-world executives as AI avatars.

INSPIRATION: BTS "SWIM" Music Video — cinematic atmosphere, emotional journey, metaphorical storytelling.
The analyst report news becomes the PLOT of a mini-drama between two powerful figures.

## Report
Stock: {stock}
Headline: {title}
Key figures: {num_str}  |  Target price: {target}
{market_str}
Report excerpt (Korean — extract the key deal/news as drama material):
{text[:1500]}

## Cast
Character A (PROTAGONIST / LEFT SIDE):
  {char_a_str}

Character B (COUNTERPART / RIGHT SIDE):
  {char_b_str}

## Story Requirements
- The DEAL / NEWS from the report = the central plot event
- Character A delivers the key news to Character B through dialogue
- Dialogue must feel REAL and CINEMATIC — not like a news summary
- Mix English and Korean naturally (bilingual dialogue works great for Korean-American audience)
- Each scene = a STORY BEAT (not just an information dump)
- Include an unexpected emotional twist or ironic reaction
- Visual direction for each scene (atmospheric, moody, BTS SWIM-like)

## Scene Structure (6 scenes + CTA):
1. ACT I — SETTING: Establish mood/location metaphor (e.g. "두 척의 배가 만났다", "태평양 한가운데")
2. ACT I — INTRO: Character A's reaction to the news (solo, emotional)
3. ACT II — DIALOGUE: Character A speaks to Character B — the KEY deal dialogue
4. ACT II — RESPONSE: Character B's response (can be surprising, skeptical, or moving)
5. ACT III — TWIST: Unexpected revelation or ironic consequence of the deal
6. ACT III — RESOLUTION: Final emotional beat / what this means for investors

visual_note options for each scene:
  "celeb_setting"   — full-screen atmospheric establishing shot (black bg, poetic text)
  "celeb_{{color}}" — character's accent color (e.g. "celeb_green" for Elon, "celeb_blue" for Samsung)
  "celeb_twist"     — dramatic reveal (dark bg, high contrast)

Respond ONLY with valid JSON:

{{
  "format_type": "celeb_collab",
  "hook_text": "The deal that changes everything 🌊 — max 65 chars, Korean or English",
  "hook_subtext": "Cinematic ironic subtitle, max 45 chars",
  "first_frame": {{
    "headline": "ACT I",
    "stat": "Key deal figure with emoji (e.g. '₩2.3조 🤝')",
    "color": "green or blue"
  }},
  "characters": [
    {{
      "name": "{char_a.name if char_a else 'Character A'}",
      "role": "{char_a.role if char_a else ''}",
      "emoji": "{char_a.emoji if char_a else '🎭'}",
      "text_color": "{char_a.text_color if char_a else 'green'}"
    }},
    {{
      "name": "{char_b.name if char_b else 'Character B'}",
      "role": "{char_b.role if char_b else ''}",
      "emoji": "{char_b.emoji if char_b else '💼'}",
      "text_color": "{char_b.text_color if char_b else 'blue'}"
    }}
  ],
  "scenes": [
    {{
      "scene_num": 1,
      "label": "ACT I · SETTING",
      "character": "",
      "dialogue": "Cinematic location/mood text — poetic, max 80 chars",
      "visual_note": "celeb_setting",
      "duration": 5,
      "emphasis": false
    }},
    {{
      "scene_num": 2,
      "label": "ACT I · {char_a.name if char_a else 'A'}",
      "character": "{char_a.name if char_a else 'A'}",
      "dialogue": "Character A's reaction line — emotional, punchy, max 90 chars",
      "visual_note": "celeb_{(char_a.text_color if char_a else 'green')}",
      "duration": 8,
      "emphasis": true
    }},
    {{
      "scene_num": 3,
      "label": "ACT II · THE DEAL",
      "character": "{char_a.name if char_a else 'A'}",
      "dialogue": "The KEY DEAL dialogue — Character A tells Character B. Max 100 chars. Must reference actual deal terms from report.",
      "visual_note": "celeb_{(char_a.text_color if char_a else 'green')}",
      "duration": 10,
      "emphasis": true
    }},
    {{
      "scene_num": 4,
      "label": "ACT II · {char_b.name if char_b else 'B'}",
      "character": "{char_b.name if char_b else 'B'}",
      "dialogue": "Character B's response — can be surprising, human, or ironic. Max 90 chars.",
      "visual_note": "celeb_{(char_b.text_color if char_b else 'blue')}",
      "duration": 8,
      "emphasis": false
    }},
    {{
      "scene_num": 5,
      "label": "ACT III · TWIST",
      "character": "",
      "dialogue": "Ironic or unexpected twist — what retail investors should actually know. Max 90 chars.",
      "visual_note": "celeb_twist",
      "duration": 8,
      "emphasis": true
    }},
    {{
      "scene_num": 6,
      "label": "ACT III · WHAT THIS MEANS",
      "character": "{char_a.name if char_a else 'A'}",
      "dialogue": "Final emotional beat / investor insight line. Punchy. Max 85 chars.",
      "visual_note": "celeb_{(char_a.text_color if char_a else 'green')}",
      "duration": 8,
      "emphasis": false
    }}
  ],
  "subtitles": [
    {{"time_start": 0,  "time_end": 3,  "text": "Hook subtitle"}},
    {{"time_start": 3,  "time_end": 8,  "text": "ACT I setting"}},
    {{"time_start": 8,  "time_end": 16, "text": "Scene 2"}},
    {{"time_start": 16, "time_end": 26, "text": "Scene 3 — the deal"}},
    {{"time_start": 26, "time_end": 34, "text": "Scene 4 — response"}},
    {{"time_start": 34, "time_end": 42, "text": "Twist"}},
    {{"time_start": 42, "time_end": 50, "text": "Resolution"}},
    {{"time_start": 53, "time_end": 60, "text": "CTA"}}
  ],
  "cta_text": "Witty CTA that fits the cinematic tone — 1 line",
  "hashtags": ["#{stock}", "#KoreanStocks", "#investing", "#shorts", "#drama"],
  "title": "Cinematic clickbait title referencing the two execs, max 80 chars",
  "description": "Short punchy description with key figures, max 200 chars"
}}"""

    def _parse_celeb_response(
        self,
        raw: str,
        report: dict,
        celeb_chars: list,
    ) -> ShortScript:
        stock = report.get("stock_name", "stock")
        try:
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(json_match.group()) if json_match else {}
        except Exception:
            data = {}

        if not data or "error" in data:
            return self._fallback_celeb_script(report, celeb_chars)

        characters = [
            Character(
                name       = c.get("name", ""),
                role       = c.get("role", ""),
                emoji      = c.get("emoji", ""),
                text_color = c.get("text_color", "white"),
            )
            for c in data.get("characters", [])
        ]

        scenes = [
            Scene(
                scene_num   = s.get("scene_num", i + 1),
                label       = s.get("label", ""),
                character   = s.get("character", ""),
                dialogue    = s.get("dialogue", ""),
                visual_note = s.get("visual_note", "celeb_setting"),
                duration    = s.get("duration", 8),
                emphasis    = s.get("emphasis", False),
            )
            for i, s in enumerate(data.get("scenes", []))
        ]

        return ShortScript(
            stock_name       = stock,
            format_type      = "celeb_collab",
            hook_text        = data.get("hook_text", f"{stock} — the deal 🌊"),
            hook_subtext     = data.get("hook_subtext", ""),
            first_frame      = data.get("first_frame", {"headline": "ACT I", "stat": "", "color": "green"}),
            characters       = characters,
            scenes           = scenes,
            subtitles        = data.get("subtitles", []),
            cta_text         = data.get("cta_text", "Follow for the inside story 🎬"),
            hashtags         = data.get("hashtags", [f"#{stock}", "#KoreanStocks", "#shorts"]),
            title            = data.get("title", f"{stock} — the untold deal #shorts"),
            description      = data.get("description", ""),
            hook_type        = "celeb_collab",
            celeb_characters = celeb_chars,
        )

    def _fallback_celeb_script(self, report: dict, celeb_chars: list) -> ShortScript:
        stock  = report.get("stock_name", "the stock")
        nums   = report.get("key_numbers", [])
        stat   = (nums[0] + " 🤝") if nums else "BIG DEAL 🤝"
        char_a = celeb_chars[0] if celeb_chars else None
        char_b = celeb_chars[1] if len(celeb_chars) > 1 else None
        a_name = char_a.name if char_a else "CEO A"
        b_name = char_b.name if char_b else "CEO B"
        a_col  = f"celeb_{char_a.text_color}" if char_a else "celeb_green"
        b_col  = f"celeb_{char_b.text_color}" if char_b else "celeb_blue"

        return ShortScript(
            stock_name       = stock,
            format_type      = "celeb_collab",
            hook_text        = f"The deal that changes everything 🌊",
            hook_subtext     = "This is not financial advice",
            first_frame      = {"headline": "ACT I", "stat": stat, "color": "green"},
            characters       = [
                Character(name=a_name, role=char_a.role if char_a else "", emoji=char_a.emoji if char_a else "🎭", text_color=char_a.text_color if char_a else "green"),
                Character(name=b_name, role=char_b.role if char_b else "", emoji=char_b.emoji if char_b else "💼", text_color=char_b.text_color if char_b else "blue"),
            ],
            scenes=[
                Scene(1, "ACT I · SETTING",        "",      "태평양 한가운데, 두 거인이 만났다", "celeb_setting", 5,  False),
                Scene(2, f"ACT I · {a_name}",       a_name, f"We need to talk about {stock}.",  a_col,           8,  True),
                Scene(3, "ACT II · THE DEAL",       a_name, f"The numbers: {stat}",              a_col,           10, True),
                Scene(4, f"ACT II · {b_name}",      b_name, "Interesting. Tell me more.",        b_col,           8,  False),
                Scene(5, "ACT III · TWIST",         "",     "What retail investors missed: 🤫",  "celeb_twist",   8,  True),
                Scene(6, "ACT III · WHAT THIS MEANS", a_name, "The market hasn't priced this yet.", a_col,        8,  False),
            ],
            subtitles=[
                {"time_start": 0,  "time_end": 3,  "text": "The deal that changes everything 🌊"},
                {"time_start": 3,  "time_end": 8,  "text": "태평양 한가운데, 두 거인이 만났다"},
                {"time_start": 8,  "time_end": 18, "text": f"{a_name}: We need to talk about {stock}"},
                {"time_start": 18, "time_end": 26, "text": f"The numbers: {stat}"},
                {"time_start": 26, "time_end": 34, "text": f"{b_name}: Interesting. Tell me more."},
                {"time_start": 34, "time_end": 42, "text": "What retail investors missed 🤫"},
                {"time_start": 42, "time_end": 50, "text": "The market hasn't priced this yet."},
                {"time_start": 53, "time_end": 60, "text": "Follow for the inside story 🎬"},
            ],
            cta_text         = "Follow for the inside story 🎬",
            hashtags         = [f"#{stock}", "#KoreanStocks", "#investing", "#shorts"],
            title            = f"{a_name} x {b_name} — The {stock} Deal #shorts",
            description      = f"The untold story behind {stock}. {', '.join(nums[:2])}",
            hook_type        = "celeb_collab",
            celeb_characters = celeb_chars,
        )

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
