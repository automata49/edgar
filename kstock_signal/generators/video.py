from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy import CompositeVideoClip, ImageClip, TextClip, concatenate_videoclips
    _MOVIEPY_OK = True
except ImportError:
    _MOVIEPY_OK = False

# ── Constants ─────────────────────────────────────────────────────────────────

W, H          = 720, 1280
FPS           = 30
HOOK_DURATION = 3
FONT_BOLD     = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
FONT_REGULAR  = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Palette
C = {
    "black":      (8,   8,   12),
    "dark":       (15,  15,  25),
    "card":       (25,  25,  42),
    "alert":      (40,  10,  10),
    "news_bg":    (12,  20,  40),
    "meme_bg":    (20,  20,  20),
    "green":      (0,   230, 118),
    "red":        (255, 82,  82),
    "yellow":     (255, 214, 0),
    "white":      (255, 255, 255),
    "gray":       (160, 160, 180),
    "blue":       (100, 149, 237),
    "news_red":   (200, 30,  30),
    "breaking":   (220, 40,  40),
    # ── Celeb collab (BTS SWIM 스타일) ────────────────────────────────────────
    "cinema_bg":  (5,   5,   20),    # 심해 같은 극도로 어두운 네이비
    "cinema_mid": (10,  12,  35),    # 씬 카드 배경
    "cinema_bar": (255, 255, 255),   # 시네마틱 레터박스 바
    "act_label":  (180, 180, 210),   # ACT I / ACT II 레이블 색
}

TEXT_COLORS = {
    "green":  C["green"],
    "red":    C["red"],
    "yellow": C["yellow"],
    "white":  C["white"],
    "gray":   C["gray"],
}


class VideoGenerator:
    """
    숏폼 영상 생성기 — 5가지 엔터테인먼트 포맷 지원.

    pov           — POV 레이블 + 1인칭 상황 묘사
    news_parody   — 브레이킹 뉴스 하단 자막 + 앵커 스타일
    character_skit— 캐릭터 이름 태그 + 대사 버블
    meme_sequence — 밈 스타일 배경 + 임팩트 폰트 느낌
    drama_twist   — 영화 자막 스타일 + 반전 레이블
    """

    def __init__(self, config: dict) -> None:
        cfg             = config.get("shortvideo", {})
        self.output_dir = Path(cfg.get("output_dir", "/tmp/shorts"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.font_bold    = FONT_BOLD    if os.path.exists(FONT_BOLD)    else FONT_FALLBACK
        self.font_regular = FONT_REGULAR if os.path.exists(FONT_REGULAR) else FONT_FALLBACK

    def generate(self, script) -> Optional[str]:
        if not _MOVIEPY_OK:
            print("   ⚠️  moviepy not installed")
            return None
        try:
            return self._build_video(script)
        except Exception as e:
            print(f"   ⚠️  Video generation failed: {e}")
            return None

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_video(self, script) -> str:
        fmt   = getattr(script, "format_type", "news_parody")
        clips = []

        # Hook clip (0~3s)
        clips.append(self._make_hook_clip(script, fmt))

        # Scene clips
        for scene in (script.scenes or []):
            clips.append(self._make_scene_clip(scene, fmt, script))

        # CTA clip
        clips.append(self._make_cta_clip(script))

        subtitle_clips = self._make_subtitle_clips(script.subtitles)

        final = CompositeVideoClip(
            [concatenate_videoclips(clips, method="compose")] + subtitle_clips,
            size=(W, H),
        )

        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in script.stock_name)
        out  = str(self.output_dir / f"{safe}_{fmt}_shorts.mp4")
        final.write_videofile(out, fps=FPS, codec="libx264", audio=False, logger=None)
        print(f"🎬 Saved: {out}")
        return out

    # ── Hook Clip ─────────────────────────────────────────────────────────────

    def _make_hook_clip(self, script, fmt: str) -> ImageClip:
        frame  = script.first_frame
        accent = C["green"] if frame.get("color") == "green" else C["red"]
        img    = self._blank(C["dark"])
        draw   = ImageDraw.Draw(img)

        if fmt == "news_parody":
            self._draw_news_bg(draw, img)
            self._draw_breaking_banner(draw, "BREAKING NEWS")
        elif fmt == "meme_sequence":
            img  = self._blank(C["meme_bg"])
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (W, H)], fill=C["meme_bg"])
        elif fmt == "drama_twist":
            img  = self._blank(C["black"])
            draw = ImageDraw.Draw(img)
            # Cinematic bars
            draw.rectangle([(0, 0),      (W, 120)], fill=(0, 0, 0))
            draw.rectangle([(0, H - 120), (W, H)], fill=(0, 0, 0))
        else:
            draw.rectangle([(0, 0), (W, 10)], fill=accent)

        # Big stat
        stat = frame.get("stat", "")
        if stat:
            self._text(draw, stat, y=H * 0.27, size=108, color=accent, bold=True)

        # Hook text
        self._text(draw, script.hook_text, y=H * 0.47, size=50, color=C["white"],
                   bold=True, max_w=W - 80)

        if script.hook_subtext:
            self._text(draw, script.hook_subtext, y=H * 0.60, size=34, color=C["gray"])

        # Format label bottom
        label = frame.get("headline", "")
        if label:
            self._draw_label_pill(draw, label, y=int(H * 0.73), accent=accent)

        return self._to_clip(img, HOOK_DURATION)

    # ── Scene Dispatcher ──────────────────────────────────────────────────────

    def _make_scene_clip(self, scene, fmt: str, script) -> ImageClip:
        dispatch = {
            "pov":            self._scene_pov,
            "news_parody":    self._scene_news,
            "character_skit": self._scene_character,
            "meme_sequence":  self._scene_meme,
            "drama_twist":    self._scene_drama,
            "celeb_collab":   self._scene_celeb,
        }
        fn = dispatch.get(fmt, self._scene_character)
        return fn(scene, script)

    # ── POV Scene ─────────────────────────────────────────────────────────────

    def _scene_pov(self, scene, script) -> ImageClip:
        img  = self._blank(C["dark"])
        draw = ImageDraw.Draw(img)

        # POV label top-left
        if scene.label:
            draw.rounded_rectangle([(30, 60), (30 + len(scene.label) * 22 + 30, 110)],
                                   radius=8, fill=C["blue"])
            self._text(draw, scene.label, y=85, size=36, color=C["white"], bold=True)

        # Main dialogue center
        self._text(draw, scene.dialogue, y=H * 0.45, size=48, color=C["white"],
                   bold=scene.emphasis, max_w=W - 80)

        # Situation context bottom
        if scene.character:
            self._text(draw, f"— {scene.character}", y=H * 0.64, size=32, color=C["gray"])

        return self._to_clip(img, scene.duration)

    # ── News Parody Scene ─────────────────────────────────────────────────────

    def _scene_news(self, scene, script) -> ImageClip:
        img  = self._blank(C["news_bg"])
        draw = ImageDraw.Draw(img)
        self._draw_news_bg(draw, img)

        # Ticker bar at bottom
        draw.rectangle([(0, H - 120), (W, H - 70)], fill=C["news_red"])
        self._text(draw, f"▶ {script.stock_name.upper()} MARKET UPDATE",
                   y=H - 95, size=30, color=C["white"], bold=True)

        # Scene label (BREAKING / ANALYST SAYS / etc.)
        if scene.label:
            self._draw_breaking_banner(draw, scene.label)

        # Main text
        self._text(draw, scene.dialogue, y=H * 0.45, size=46, color=C["white"],
                   bold=scene.emphasis, max_w=W - 60)

        # Reporter name tag
        if scene.character:
            draw.rectangle([(0, H * 0.65), (W, H * 0.72)], fill=C["blue"])
            self._text(draw, scene.character, y=H * 0.685, size=30, color=C["white"], bold=True)

        return self._to_clip(img, scene.duration)

    # ── Character Skit Scene ──────────────────────────────────────────────────

    def _scene_character(self, scene, script) -> ImageClip:
        char_color = self._resolve_char_color(scene.character, script)
        bg_color   = C["alert"] if scene.visual_note == "alert" else C["card"]
        img        = self._blank(bg_color)
        draw       = ImageDraw.Draw(img)

        # Vertical accent stripe
        draw.rectangle([(0, 0), (8, H)], fill=char_color)

        # Character name tag
        if scene.character:
            tag_w = len(scene.character) * 20 + 40
            draw.rounded_rectangle([(30, H * 0.22), (30 + tag_w, H * 0.22 + 52)],
                                   radius=10, fill=char_color)
            self._text(draw, scene.character, y=H * 0.248, size=34,
                       color=C["black"], bold=True)

        # Dialogue bubble
        draw.rounded_rectangle([(30, H * 0.33), (W - 30, H * 0.62)],
                                radius=16, fill=C["dark"])
        self._text(draw, scene.dialogue, y=H * 0.47, size=44, color=C["white"],
                   bold=scene.emphasis, max_w=W - 100)

        # Emoji from character pool if available
        emoji = self._resolve_char_emoji(scene.character, script)
        if emoji:
            self._text(draw, emoji, y=H * 0.70, size=72, color=C["white"])

        return self._to_clip(img, scene.duration)

    # ── Meme Sequence Scene ───────────────────────────────────────────────────

    def _scene_meme(self, scene, script) -> ImageClip:
        img  = self._blank(C["meme_bg"])
        draw = ImageDraw.Draw(img)

        # Bold top label (meme caption style)
        if scene.label:
            draw.rectangle([(0, 0), (W, 100)], fill=C["black"])
            self._text(draw, scene.label.upper(), y=50, size=44,
                       color=C["yellow"], bold=True, max_w=W - 40)

        # Center main text — large, impactful
        self._text(draw, scene.dialogue, y=H * 0.46, size=52, color=C["white"],
                   bold=True, max_w=W - 60)

        # Bottom reaction
        if scene.character:
            draw.rectangle([(0, H - 110), (W, H)], fill=C["black"])
            self._text(draw, scene.character, y=H - 55, size=30, color=C["gray"])

        return self._to_clip(img, scene.duration)

    # ── Drama Twist Scene ─────────────────────────────────────────────────────

    def _scene_drama(self, scene, script) -> ImageClip:
        img  = self._blank(C["black"])
        draw = ImageDraw.Draw(img)

        # Cinematic bars
        draw.rectangle([(0, 0),       (W, 100)], fill=(0, 0, 0))
        draw.rectangle([(0, H - 100), (W, H)],   fill=(0, 0, 0))

        # Scene label — film subtitle style
        if scene.label:
            self._text(draw, scene.label, y=H * 0.22, size=34, color=C["yellow"])

        # Main dialogue — centered, high contrast
        self._text(draw, scene.dialogue, y=H * 0.47, size=50,
                   color=C["white"] if not scene.emphasis else C["yellow"],
                   bold=scene.emphasis, max_w=W - 80)

        # Subtle character credit
        if scene.character:
            self._text(draw, f"— {scene.character}", y=H * 0.65, size=28, color=C["gray"])

        return self._to_clip(img, scene.duration)

    # ── Celeb Collab Scene (BTS SWIM 스타일 시네마틱) ─────────────────────────

    def _scene_celeb(self, scene, script) -> ImageClip:
        """
        시네마틱 씬 렌더러 — visual_note에 따라 3가지 레이아웃:

        "celeb_setting"  — 전체화면 배경 + 시적 텍스트 (분위기 확립)
        "celeb_{color}"  — 캐릭터 포커스: 이름 타이틀 카드 + 대사
        "celeb_twist"    — 전체화면 반전 씬: 고대비 + 강렬한 텍스트
        """
        vn = scene.visual_note or "celeb_setting"

        if vn == "celeb_setting":
            return self._celeb_setting_frame(scene)
        if vn == "celeb_twist":
            return self._celeb_twist_frame(scene)
        # "celeb_green" / "celeb_blue" / "celeb_yellow" / "celeb_white" / "celeb_gray"
        color_key = vn.replace("celeb_", "") if vn.startswith("celeb_") else "white"
        return self._celeb_character_frame(scene, script, color_key)

    def _celeb_setting_frame(self, scene) -> ImageClip:
        """ACT 도입부 — BTS SWIM 오프닝처럼 어두운 전체화면 + 시적 텍스트."""
        img  = self._blank(C["cinema_bg"])
        draw = ImageDraw.Draw(img)

        # 레터박스 바 (시네마틱 느낌)
        bar_h = 70
        draw.rectangle([(0, 0),       (W, bar_h)],      fill=(0, 0, 0))
        draw.rectangle([(0, H - bar_h), (W, H)],        fill=(0, 0, 0))

        # ACT 레이블 (상단 바 안)
        if scene.label:
            self._text(draw, scene.label, y=bar_h // 2, size=24,
                       color=C["act_label"], bold=False)

        # 수평 분리선
        draw.line([(60, H // 2 - 2), (W - 60, H // 2 - 2)], fill=(50, 50, 80), width=1)

        # 시적 대사 — 중앙 배치
        self._text(draw, scene.dialogue, y=H * 0.48, size=44,
                   color=C["white"], bold=False, max_w=W - 100)

        # 씬 번호 (하단 바 안) — 영화 자막 느낌
        self._text(draw, f"— {scene.scene_num:02d} —", y=H - bar_h // 2,
                   size=22, color=C["act_label"])

        return self._to_clip(img, scene.duration)

    def _celeb_character_frame(self, scene, script, color_key: str) -> ImageClip:
        """
        캐릭터 포커스 씬 — 이름 타이틀 카드 + 대사 버블.

        레이아웃 (세로):
          ┌─────────────────────────┐
          │  [레터박스]              │  ← 70px
          │                         │
          │  ████████████████████   │  ← ACT 레이블
          │                         │
          │  CHARACTER NAME         │  ← 큰 이름 (캐릭터 컬러)
          │  Role · Company         │  ← 작은 역할
          │                         │
          │  ┌─────────────────────┐│
          │  │  대화 텍스트          ││  ← 버블 박스
          │  └─────────────────────┘│
          │                         │
          │  emoji                  │
          │  [레터박스]              │  ← 70px
          └─────────────────────────┘
        """
        accent = TEXT_COLORS.get(color_key, C["white"])
        img    = self._blank(C["cinema_bg"])
        draw   = ImageDraw.Draw(img)

        # 레터박스
        bar_h = 70
        draw.rectangle([(0, 0),         (W, bar_h)],      fill=(0, 0, 0))
        draw.rectangle([(0, H - bar_h), (W, H)],          fill=(0, 0, 0))

        # 캐릭터 컬러 사이드 스트라이프 (좌측 4px)
        draw.rectangle([(0, bar_h), (5, H - bar_h)], fill=accent)

        # ACT 레이블
        if scene.label:
            self._text(draw, scene.label, y=bar_h // 2, size=22,
                       color=C["act_label"], bold=False)

        # 캐릭터 이름 (크고 굵게, 캐릭터 컬러)
        name_y = H * 0.26
        if scene.character:
            self._text(draw, scene.character, y=name_y, size=52,
                       color=accent, bold=True, max_w=W - 80)

        # 역할/회사 (작은 텍스트)
        role = self._resolve_char_role(scene.character, script)
        if role:
            self._text(draw, role, y=name_y + 60, size=26,
                       color=C["gray"], bold=False)

        # 대사 버블 박스
        bubble_y0 = int(H * 0.44)
        bubble_y1 = int(H * 0.72)
        draw.rounded_rectangle(
            [(30, bubble_y0), (W - 30, bubble_y1)],
            radius=18, fill=C["cinema_mid"],
        )
        # 버블 테두리 (캐릭터 컬러 얇게)
        draw.rounded_rectangle(
            [(30, bubble_y0), (W - 30, bubble_y1)],
            radius=18, outline=accent, width=2,
        )

        self._text(draw, scene.dialogue,
                   y=(bubble_y0 + bubble_y1) // 2,
                   size=40 if scene.emphasis else 36,
                   color=C["white"], bold=scene.emphasis, max_w=W - 100)

        # 이모지 (하단)
        emoji = self._resolve_char_emoji(scene.character, script)
        if emoji:
            self._text(draw, emoji, y=H * 0.79, size=56, color=C["white"])

        return self._to_clip(img, scene.duration)

    def _celeb_twist_frame(self, scene) -> ImageClip:
        """ACT III 반전 씬 — 강렬한 고대비 + 충격 텍스트."""
        img  = self._blank(C["black"])
        draw = ImageDraw.Draw(img)

        # 레터박스
        bar_h = 70
        draw.rectangle([(0, 0),         (W, bar_h)],  fill=(0, 0, 0))
        draw.rectangle([(0, H - bar_h), (W, H)],      fill=(0, 0, 0))

        # 빨간 수평선 (긴장감)
        draw.rectangle([(0, H // 2 - 2), (W, H // 2 + 2)], fill=C["red"])

        # ACT 레이블
        if scene.label:
            self._text(draw, scene.label, y=bar_h // 2, size=22,
                       color=(200, 80, 80), bold=False)

        # 메인 반전 텍스트
        self._text(draw, scene.dialogue, y=H * 0.47, size=48,
                   color=C["yellow"], bold=True, max_w=W - 80)

        return self._to_clip(img, scene.duration)

    # ── Hook Override for celeb_collab ────────────────────────────────────────

    def _make_hook_clip(self, script, fmt: str) -> ImageClip:
        if fmt == "celeb_collab":
            return self._celeb_hook_clip(script)
        return self._make_hook_clip_default(script, fmt)

    def _celeb_hook_clip(self, script) -> ImageClip:
        """BTS SWIM 오프닝 스타일 훅 클립."""
        img  = self._blank(C["cinema_bg"])
        draw = ImageDraw.Draw(img)

        # 레터박스
        bar_h = 70
        draw.rectangle([(0, 0),         (W, bar_h)],  fill=(0, 0, 0))
        draw.rectangle([(0, H - bar_h), (W, H)],      fill=(0, 0, 0))

        # 배지
        frame = script.first_frame
        badge = frame.get("headline", "ACT I")
        self._text(draw, badge, y=bar_h // 2, size=24,
                   color=C["act_label"], bold=False)

        # 핵심 수치 (큰 텍스트)
        stat = frame.get("stat", "")
        accent = C["green"] if frame.get("color") == "green" else C["blue"]
        if stat:
            self._text(draw, stat, y=H * 0.30, size=80, color=accent, bold=True)

        # 훅 텍스트
        self._text(draw, script.hook_text, y=H * 0.50, size=46,
                   color=C["white"], bold=True, max_w=W - 80)

        if script.hook_subtext:
            self._text(draw, script.hook_subtext, y=H * 0.62, size=30,
                       color=C["act_label"])

        # 캐릭터 이름들 (하단)
        chars = getattr(script, "celeb_characters", None) or []
        if len(chars) >= 2:
            pair = f"{chars[0].name}  ×  {chars[1].name}"
            self._text(draw, pair, y=H * 0.76, size=28, color=C["gray"])

        return self._to_clip(img, HOOK_DURATION)

    def _make_hook_clip_default(self, script, fmt: str) -> ImageClip:
        """기존 훅 클립 로직 (celeb_collab 외 포맷)."""
        frame  = script.first_frame
        accent = C["green"] if frame.get("color") == "green" else C["red"]
        img    = self._blank(C["dark"])
        draw   = ImageDraw.Draw(img)

        if fmt == "news_parody":
            self._draw_news_bg(draw, img)
            self._draw_breaking_banner(draw, "BREAKING NEWS")
        elif fmt == "meme_sequence":
            img  = self._blank(C["meme_bg"])
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (W, H)], fill=C["meme_bg"])
        elif fmt == "drama_twist":
            img  = self._blank(C["black"])
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0),      (W, 120)], fill=(0, 0, 0))
            draw.rectangle([(0, H - 120), (W, H)], fill=(0, 0, 0))
        else:
            draw.rectangle([(0, 0), (W, 10)], fill=accent)

        stat = frame.get("stat", "")
        if stat:
            self._text(draw, stat, y=H * 0.27, size=108, color=accent, bold=True)

        self._text(draw, script.hook_text, y=H * 0.47, size=50, color=C["white"],
                   bold=True, max_w=W - 80)

        if script.hook_subtext:
            self._text(draw, script.hook_subtext, y=H * 0.60, size=34, color=C["gray"])

        label = frame.get("headline", "")
        if label:
            self._draw_label_pill(draw, label, y=int(H * 0.73), accent=accent)

        return self._to_clip(img, HOOK_DURATION)

    # ── Character Role Helper (celeb용) ───────────────────────────────────────

    def _resolve_char_role(self, name: str, script) -> str:
        """celeb_characters 또는 characters에서 역할 텍스트 조회."""
        celeb_chars = getattr(script, "celeb_characters", None) or []
        for c in celeb_chars:
            if c.name == name:
                return c.role
        for c in getattr(script, "characters", []):
            if c.name == name:
                return c.role
        return ""

    # ── CTA Clip ──────────────────────────────────────────────────────────────

    def _make_cta_clip(self, script) -> ImageClip:
        fmt    = getattr(script, "format_type", "news_parody")
        accent = C["red"] if fmt in ("drama_twist", "news_parody") else C["blue"]
        img    = self._blank(C["dark"])
        draw   = ImageDraw.Draw(img)

        draw.rounded_rectangle([(40, H * 0.30), (W - 40, H * 0.58)],
                               radius=24, fill=accent)
        self._text(draw, script.cta_text, y=H * 0.43, size=42,
                   color=C["white"], bold=True, max_w=W - 120)

        tags = "  ".join(script.hashtags[:4])
        self._text(draw, tags, y=H * 0.63, size=28, color=C["gray"])

        return self._to_clip(img, 10)

    # ── Subtitles ─────────────────────────────────────────────────────────────

    def _make_subtitle_clips(self, subtitles: list[dict]) -> list:
        clips = []
        for sub in subtitles:
            t0   = sub.get("time_start", 0)
            t1   = sub.get("time_end", t0 + 3)
            text = sub.get("text", "")
            if not text:
                continue
            try:
                tc = (
                    TextClip(
                        text=text,
                        font_size=34,
                        color="white",
                        stroke_color="black",
                        stroke_width=2,
                        size=(W - 80, None),
                        method="caption",
                    )
                    .with_position(("center", int(H * 0.82)))
                    .with_start(t0)
                    .with_end(t1)
                )
                clips.append(tc)
            except Exception:
                pass
        return clips

    # ── Draw Helpers ──────────────────────────────────────────────────────────

    def _draw_news_bg(self, draw: ImageDraw.ImageDraw, img: Image.Image) -> None:
        draw.rectangle([(0, 0), (W, H)], fill=C["news_bg"])
        # subtle grid lines
        for y in range(0, H, 80):
            draw.line([(0, y), (W, y)], fill=(20, 30, 50), width=1)

    def _draw_breaking_banner(self, draw: ImageDraw.ImageDraw, label: str) -> None:
        draw.rectangle([(0, 60), (W, 115)], fill=C["breaking"])
        self._text(draw, f"▶ {label}", y=88, size=36, color=C["white"], bold=True)

    def _draw_label_pill(self, draw: ImageDraw.ImageDraw, label: str,
                         y: int, accent: tuple) -> None:
        tw  = len(label) * 22 + 40
        x0  = (W - tw) // 2
        draw.rounded_rectangle([(x0, y - 24), (x0 + tw, y + 28)], radius=10, fill=accent)
        self._text(draw, label, y=y, size=34, color=C["black"], bold=True)

    # ── Character Helpers ─────────────────────────────────────────────────────

    def _resolve_char_color(self, name: str, script) -> tuple:
        for c in getattr(script, "characters", []):
            if c.name == name:
                return TEXT_COLORS.get(c.text_color, C["white"])
        return C["blue"]

    def _resolve_char_emoji(self, name: str, script) -> str:
        for c in getattr(script, "characters", []):
            if c.name == name:
                return c.emoji
        return ""

    # ── PIL Utilities ─────────────────────────────────────────────────────────

    def _blank(self, color: tuple) -> Image.Image:
        return Image.new("RGB", (W, H), color)

    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        path = self.font_bold if bold else self.font_regular
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()

    def _text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        y: float,
        size: int,
        color: tuple,
        bold: bool = False,
        max_w: int = W - 60,
    ) -> None:
        if not text:
            return
        font    = self._font(size, bold)
        wrap_w  = max(8, max_w // max(size // 2, 1))
        wrapped = textwrap.fill(str(text), width=wrap_w)
        lines   = wrapped.split("\n")
        line_h  = size + 10
        cur_y   = int(y) - (line_h * len(lines)) // 2

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw   = bbox[2] - bbox[0]
            x    = (W - tw) // 2
            # Drop shadow
            draw.text((x + 2, cur_y + 2), line, font=font, fill=(0, 0, 0))
            draw.text((x, cur_y), line, font=font, fill=color)
            cur_y += line_h

    def _to_clip(self, img: Image.Image, duration: float) -> ImageClip:
        import numpy as np
        return ImageClip(np.array(img), duration=duration)
