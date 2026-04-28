from __future__ import annotations

import asyncio
import io
import os
import random
import subprocess
import tempfile
import threading
import wave
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    from moviepy import (
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        ImageClip,
        VideoClip,
        VideoFileClip,
        concatenate_videoclips,
    )
    import moviepy.video.fx as mvfx
    _MOVIEPY_OK = True
except ImportError:
    _MOVIEPY_OK = False

try:
    import fal_client
    _FAL_OK = True
except ImportError:
    _FAL_OK = False

try:
    import edge_tts
    _TTS_OK = True
except ImportError:
    _TTS_OK = False

import requests

W, H  = 720, 1280
FPS   = 30
FONT_BOLD     = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
FONT_REGULAR  = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ── Cinematic Prompt Library ──────────────────────────────────────────────────

_QUALITY = (
    "cinematic photography, ultra detailed, 8K resolution, professional lighting, "
    "dramatic atmosphere, shallow depth of field, high contrast, sharp focus"
)

_FORMAT_PROMPTS: dict[str, str] = {
    "news_parody": (
        "modern television news broadcast studio at night, dramatic red and blue ambient glow, "
        "multiple holographic screens showing stock charts and financial data, "
        "professional TV set, dark polished floor reflecting lights, "
    ),
    "character_skit": (
        "moody urban trading floor environment, dark atmospheric space, "
        "glowing monitor arrays showing stock charts, bokeh city lights background, "
    ),
    "meme_sequence": (
        "bold graphic digital art background, vibrant neon grid, internet culture aesthetic, "
        "dark vignette edges, high contrast geometric patterns, "
    ),
    "drama_twist": (
        "cinematic thriller atmosphere, single dramatic spotlight in darkness, "
        "smoke and dust particles, film noir shadows, letterbox composition, "
    ),
    "pov": (
        "first-person view of hands holding smartphone showing stock trading app, "
        "real-time candlestick chart, notification alerts, dramatic ambient light, "
    ),
    "celeb_collab": (
        "ultra-luxury executive boardroom at night, floor-to-ceiling windows revealing city skyline, "
        "warm directional lighting on mahogany conference table, "
        "two figures in silhouette against glowing city backdrop, "
    ),
}

_VISUAL_NOTE_PROMPTS: dict[str, str] = {
    "celeb_setting": (
        "epic ocean vista at night, moonlit waves, two distant silhouettes on cliffside, "
        "atmospheric fog rolling in, stars reflecting on water, "
    ),
    "celeb_twist": (
        "dramatic revelation scene, deep crimson emergency lighting, "
        "dark control room, tension-filled atmosphere, single intense spotlight, "
    ),
    "alert": (
        "emergency red alert atmosphere, dark control room lit by warning lights, "
        "crisis command center, high stakes environment, "
    ),
    "news": (
        "breaking news broadcast desk, dramatic studio lighting, "
        "holographic market data displays surrounding anchor position, "
    ),
    "meme": (
        "internet meme visual aesthetic, retro computer screen glow, "
        "pixelated art style with cinematic depth, bold dark background, "
    ),
    "dark": (
        "dark moody executive office, city lights visible through rain-streaked windows, "
        "single desk lamp, luxury minimal decor, "
    ),
    "card": (
        "clean corporate meeting room, soft window light from behind, "
        "blurred city background, professional atmosphere, "
    ),
}

_COLOR_PROMPTS: dict[str, str] = {
    "green":  "emerald green accent lighting, bullish growth energy, financial uptrend glow, ",
    "red":    "deep crimson danger lighting, market crash atmosphere, urgent red warning light, ",
    "yellow": "golden amber warm accent, earnings announcement atmosphere, ",
    "blue":   "electric blue corporate lighting, technology and innovation glow, ",
    "white":  "clean bright studio lighting, minimal high-key atmosphere, ",
}


class AIVideoGenerator:
    """
    Sora급 AI 숏폼 영상 생성기 — 오픈소스 모델 사용.

    Backends (config shortvideo.ai_backend):
      pollinations — Pollinations.ai Flux.1  키 불필요·완전 무료  ← 기본값
      hf           — HuggingFace FLUX.1-schnell  무료(HF_TOKEN 권장)
      flux         — fal.ai Flux  고품질 (~$0.02/영상, FAL_KEY 필요)
      wan2         — fal.ai Wan2.1 실제 AI 동영상 (~$0.30/영상, FAL_KEY 필요)
      pil          — 향상된 PIL 그래디언트 렌더러  완전 로컬
    """

    def __init__(self, config: dict) -> None:
        cfg             = config.get("shortvideo", {})
        self.output_dir = Path(cfg.get("output_dir", "/tmp/shorts"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.backend    = cfg.get("ai_backend", "pollinations")
        self.fal_key    = config.get("fal_api_key") or os.getenv("FAL_KEY", "")
        self.hf_token   = os.getenv("HF_TOKEN", "")
        self.font_bold    = FONT_BOLD    if os.path.exists(FONT_BOLD)    else FONT_FALLBACK
        self.font_regular = FONT_REGULAR if os.path.exists(FONT_REGULAR) else FONT_FALLBACK

        if self.fal_key:
            os.environ["FAL_KEY"] = self.fal_key

        if not _FAL_OK and self.backend in ("wan2", "flux"):
            print("   ⚠️  fal-client 미설치 → pollinations 폴백")
            self.backend = "pollinations"
        elif not self.fal_key and self.backend in ("wan2", "flux"):
            print("   ⚠️  FAL_KEY 미설정 → pollinations 폴백")
            self.backend = "pollinations"

        if not _TTS_OK:
            print("   ⚠️  edge-tts 미설치 — TTS 비활성")

    # ── Public ────────────────────────────────────────────────────────────────

    def generate(self, script) -> Optional[str]:
        if not _MOVIEPY_OK:
            print("   ⚠️  moviepy 미설치")
            return None
        try:
            return self._build_video(script)
        except Exception as e:
            import traceback
            print(f"   ⚠️  AI 영상 생성 실패: {e}")
            traceback.print_exc()
            return None

    # ── Pipeline ──────────────────────────────────────────────────────────────

    def _build_video(self, script) -> str:
        fmt = getattr(script, "format_type", "news_parody")
        print(f"   🎬 [{self.backend.upper()}] {script.stock_name} / {fmt}")

        # 씬 명세 목록 수집 (scene, text, subtext, dur, is_hook, is_cta)
        specs = self._collect_specs(script)

        # AI 백엔드: 모든 배경 이미지를 병렬로 사전 생성 → 전체 시간 ≈ 1장 시간
        bg_imgs = self._prefetch_backgrounds(specs, script, fmt)

        # 클립 조립
        clips: list = []
        for i, (scene, text, subtext, dur, is_hook, is_cta) in enumerate(specs):
            clips.append(self._make_scene_clip(
                scene=scene, script=script, fmt=fmt,
                text=text, subtext=subtext, duration=dur,
                is_hook=is_hook, is_cta=is_cta,
                prefetched_img=bg_imgs[i],
            ))

        clips = self._apply_crossfades(clips)
        video = concatenate_videoclips(clips, method="compose")
        video = self._mix_audio(video, script)

        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in script.stock_name)
        out  = str(self.output_dir / f"{safe}_{fmt}_ai_shorts.mp4")
        video.write_videofile(out, fps=FPS, codec="libx264", audio_codec="aac", logger=None)
        print(f"   ✅ 저장: {out}")
        return out

    # ── Spec Collection ───────────────────────────────────────────────────────

    def _collect_specs(self, script) -> list[tuple]:
        """(scene, text, subtext, duration, is_hook, is_cta) 튜플 목록."""
        specs = [(None, script.hook_text, script.hook_subtext, 3.0, True, False)]
        for scene in (script.scenes or []):
            specs.append((
                scene,
                scene.dialogue,
                f"{scene.label}  {scene.character}".strip(),
                float(scene.duration),
                False, False,
            ))
        specs.append((
            None,
            script.cta_text,
            "  ".join((script.hashtags or [])[:4]),
            5.0, False, True,
        ))
        return specs

    # ── Parallel Background Prefetch ──────────────────────────────────────────

    def _prefetch_backgrounds(
        self,
        specs: list[tuple],
        script,
        fmt: str,
    ) -> list[Optional[Image.Image]]:
        """
        AI 배경 이미지 생성.
          pollinations / horde → 순차 처리 (IP당 동시 1건 제한)
          flux / hf            → 병렬 처리
        """
        if self.backend not in ("pollinations", "horde", "hf", "flux"):
            return [None] * len(specs)

        results: list[Optional[Image.Image]] = [None] * len(specs)
        n = len(specs)

        if self.backend in ("pollinations", "horde"):
            for i, spec in enumerate(specs):
                prompt = self._build_prompt(spec[0], script, fmt)
                print(f"      🎨 배경 {i+1}/{n}…")
                try:
                    results[i] = self._fetch_ai_image(prompt)
                except Exception as e:
                    print(f"      ⚠️  [{i+1}] 실패 → PIL ({e})")
        else:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            def fetch_one(idx: int, scene) -> tuple[int, Optional[Image.Image]]:
                try:
                    return idx, self._fetch_ai_image(self._build_prompt(scene, script, fmt))
                except Exception as e:
                    print(f"      ⚠️  [{idx}] 실패 → PIL ({e})")
                    return idx, None

            workers = min(n, 6)
            print(f"      ⚡ {n}개 배경 병렬 생성 ({workers}w)…")
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(fetch_one, i, s[0]): i for i, s in enumerate(specs)}
                for fut in as_completed(futures):
                    idx, img = fut.result()
                    results[idx] = img

        ok = sum(1 for x in results if x is not None)
        print(f"      ✅ 배경 {ok}/{n} 완료")
        return results

    def _fetch_ai_image(self, prompt: str) -> Optional[Image.Image]:
        """백엔드에 맞는 AI 이미지 한 장 생성."""
        if self.backend == "pollinations":
            return self._pollinations_fetch(prompt)
        if self.backend == "horde":
            return self._horde_fetch(prompt)
        if self.backend == "hf":
            return self._hf_fetch(prompt)
        if self.backend == "flux":
            return self._flux_fetch(prompt)
        return None

    # ── Scene Clip Builder ────────────────────────────────────────────────────

    def _make_scene_clip(
        self,
        scene,
        script,
        fmt: str,
        text: str,
        subtext: str = "",
        duration: float = 8.0,
        is_hook: bool = False,
        is_cta: bool = False,
        prefetched_img: Optional[Image.Image] = None,
    ):
        bg = self._generate_background(
            scene, script, fmt, duration, prefetched_img=prefetched_img
        )
        overlays = self._build_text_overlays(
            text=text, subtext=subtext, duration=duration,
            is_hook=is_hook, is_cta=is_cta,
            fmt=fmt, script=script, scene=scene,
        )
        if overlays:
            return CompositeVideoClip([bg] + overlays, size=(W, H))
        return bg

    # ── Background Generators ─────────────────────────────────────────────────

    def _generate_background(
        self, scene, script, fmt, duration,
        prefetched_img: Optional[Image.Image] = None,
    ):
        # 사전 생성된 AI 이미지가 있으면 바로 Ken Burns 적용
        if prefetched_img is not None:
            direction = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])
            return self._ken_burns(np.array(prefetched_img), duration, direction=direction)

        if self.backend == "wan2":
            return self._bg_wan2(scene, script, fmt, duration)
        if self.backend in ("flux", "pollinations", "hf"):
            # 단독 호출 시 개별 생성 (병렬 prefetch 없이 실행된 경우)
            img = self._fetch_ai_image(self._build_prompt(scene, script, fmt))
            if img:
                direction = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])
                return self._ken_burns(np.array(img), duration, direction=direction)
            return self._bg_pil(scene, script, fmt, duration)
        return self._bg_pil(scene, script, fmt, duration)

    # Wan2.1 ──────────────────────────────────────────────────────────────────

    def _bg_wan2(self, scene, script, fmt, duration):
        prompt = self._build_prompt(scene, script, fmt, for_video=True)
        try:
            print(f"      🤖 Wan2.1 clip ({duration:.0f}s)…")
            result = fal_client.subscribe(
                "fal-ai/wan/v2.1/1.3b/text-to-video",
                arguments={
                    "prompt": prompt,
                    "aspect_ratio": "9:16",
                    "num_frames": min(81, max(17, int(duration * 16))),
                },
            )
            url = result["video"]["url"]
            return self._url_to_clip(url, duration)
        except Exception as e:
            print(f"      ⚠️  Wan2.1 실패 ({e}) → Flux")
            return self._bg_flux(scene, script, fmt, duration)

    # Flux (fal.ai — 하위 호환용) ─────────────────────────────────────────────

    def _bg_flux(self, scene, script, fmt, duration):
        try:
            img = self._flux_fetch(self._build_prompt(scene, script, fmt))
            direction = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])
            return self._ken_burns(np.array(img), duration, direction=direction)
        except Exception as e:
            print(f"      ⚠️  Flux 실패 ({e}) → PIL")
            return self._bg_pil(scene, script, fmt, duration)

    # ── Per-image fetch helpers (병렬 prefetch용) ─────────────────────────────

    def _pollinations_fetch(self, prompt: str) -> Optional[Image.Image]:
        """
        Pollinations.ai — API 키 없이 Flux.1 이미지 생성.
        오픈소스 모델(black-forest-labs/FLUX.1-dev) 무료 서빙.
        https://pollinations.ai
        """
        from urllib.parse import quote
        seed = random.randint(0, 999999)
        url  = (
            f"https://image.pollinations.ai/prompt/{quote(prompt)}"
            f"?width={W}&height={H}&model=flux&seed={seed}"
            f"&nologo=true&nofeed=true&enhance=false"
        )
        r = requests.get(url, timeout=90, headers={"User-Agent": "Edgar-Bot/1.0"})
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB").resize((W, H), Image.LANCZOS)

    def _hf_fetch(self, prompt: str) -> Optional[Image.Image]:
        """
        HuggingFace Serverless Inference — FLUX.1-schnell (오픈소스).
        토큰: https://huggingface.co/settings/tokens (무료 계정)
        """
        headers = {"Authorization": f"Bearer {self.hf_token}"} if self.hf_token else {}
        payload = {
            "inputs": prompt,
            "parameters": {"width": W, "height": H, "num_inference_steps": 4},
        }
        hf_url = (
            "https://router.huggingface.co/hf-inference/models"
            "/black-forest-labs/FLUX.1-schnell"
        )
        r = requests.post(hf_url, headers=headers, json=payload, timeout=90)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB").resize((W, H), Image.LANCZOS)

    def _horde_fetch(self, prompt: str) -> Optional[Image.Image]:
        """
        StableHorde — 커뮤니티 GPU 기반 완전 무료 오픈소스 (MIT).
        https://stablehorde.net
        HORDE_TOKEN 없이 익명 키(0000000000)로도 동작하나 대기시간이 길어짐.
        무료 계정 등록 후 토큰 사용 권장.
        """
        import base64, time as _time

        horde_key = os.getenv("HORDE_TOKEN", "0000000000")
        submit_url = "https://stablehorde.net/api/v2/generate/async"
        headers    = {"apikey": horde_key, "Content-Type": "application/json"}

        # StableHorde는 특정 해상도 조합만 지원 (64의 배수)
        payload = {
            "prompt": prompt,
            "params": {
                "width": 768, "height": 1344,  # 9:16 portrait, 64의 배수
                "steps": 20,
                "sampler_name": "k_euler_a",
                "cfg_scale": 7.0,
                "karras": True,
            },
            "models": ["SDXL 1.0"],
            "nsfw": False,
            "censor_nsfw": True,
            "r2": False,
        }
        r = requests.post(submit_url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        job_id = r.json().get("id")
        if not job_id:
            raise ValueError(f"StableHorde 작업 ID 없음: {r.text[:200]}")

        # 완료 대기 (최대 10분)
        deadline = _time.time() + 600
        while _time.time() < deadline:
            _time.sleep(8)
            check = requests.get(
                f"https://stablehorde.net/api/v2/generate/check/{job_id}",
                headers=headers, timeout=15,
            ).json()
            if check.get("done"):
                break
            wait = check.get("wait_time", "?")
            queue = check.get("queue_position", "?")
            print(f"         horde 대기: {wait}s / 큐 {queue}번…")
        else:
            raise TimeoutError("StableHorde 시간 초과 (10분)")

        status = requests.get(
            f"https://stablehorde.net/api/v2/generate/status/{job_id}",
            headers=headers, timeout=15,
        ).json()
        img_b64 = status["generations"][0]["img"]
        img_data = base64.b64decode(img_b64)
        return Image.open(io.BytesIO(img_data)).convert("RGB").resize((W, H), Image.LANCZOS)

    def _flux_fetch(self, prompt: str) -> Optional[Image.Image]:
        """fal.ai Flux Dev — 고품질 (FAL_KEY 필요)."""
        result = fal_client.subscribe(
            "fal-ai/flux/dev",
            arguments={
                "prompt": prompt,
                "image_size": {"width": W, "height": H},
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
                "enable_safety_checker": True,
            },
        )
        url = result["images"][0]["url"]
        r   = requests.get(url, timeout=30)
        return Image.open(io.BytesIO(r.content)).convert("RGB").resize((W, H), Image.LANCZOS)

    # PIL Enhanced ────────────────────────────────────────────────────────────

    def _bg_pil(self, scene, script, fmt, duration, is_hook=False, is_cta=False):
        img = self._render_pil_bg(scene, script, fmt)
        return self._ken_burns(np.array(img), duration, zoom=1.06, direction="zoom_in")

    def _render_pil_bg(self, scene, script, fmt) -> Image.Image:
        img  = Image.new("RGB", (W, H), (8, 8, 12))
        draw = ImageDraw.Draw(img)

        # Vertical gradient
        palettes = {
            "celeb_collab":   [(5, 5, 20),   (15, 15, 45)],
            "news_parody":    [(8, 15, 35),   (20, 25, 55)],
            "drama_twist":    [(5, 5, 8),     (15, 12, 18)],
            "meme_sequence":  [(10, 10, 10),  (25, 20, 35)],
            "pov":            [(5, 12, 25),   (15, 25, 45)],
            "character_skit": [(12, 12, 22),  (22, 20, 38)],
        }
        top_col, bot_col = palettes.get(fmt, [(8, 8, 20), (18, 18, 35)])
        for y in range(H):
            t = y / H
            r = int(top_col[0] + (bot_col[0] - top_col[0]) * t)
            g = int(top_col[1] + (bot_col[1] - top_col[1]) * t)
            b = int(top_col[2] + (bot_col[2] - top_col[2]) * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

        # Grid lines (neo-Tokyo)
        for y in range(0, H, 80):
            draw.line([(0, y), (W, y)], fill=(30, 30, 60))
        for x in range(0, W, 80):
            draw.line([(x, 0), (x, H)], fill=(30, 30, 60))

        # Bokeh orbs
        vn  = getattr(scene, 'visual_note', '') or ''
        rng = random.Random(hash(vn + fmt))
        orb_layer = Image.new("RGB", (W, H), (0, 0, 0))
        orb_draw  = ImageDraw.Draw(orb_layer)
        for _ in range(18):
            cx = rng.randint(0, W)
            cy = rng.randint(0, H)
            cr = rng.randint(15, 90)
            col = self._accent_rgb(scene, fmt, dim=True)
            orb_draw.ellipse([(cx-cr, cy-cr), (cx+cr, cy+cr)], fill=col)
        orb_layer = orb_layer.filter(ImageFilter.GaussianBlur(35))
        img = Image.blend(img, orb_layer, 0.45)
        draw = ImageDraw.Draw(img)

        # Letterbox bars
        bar_h = 55
        draw.rectangle([(0, 0),          (W, bar_h)],   fill=(0, 0, 0))
        draw.rectangle([(0, H - bar_h),  (W, H)],       fill=(0, 0, 0))

        # Left accent stripe
        accent = self._accent_rgb(scene, fmt)
        for i in range(5):
            alpha = int(255 * (1 - i / 5))
            r2, g2, b2 = accent
            draw.rectangle(
                [(i, bar_h), (i + 1, H - bar_h)],
                fill=(r2 * alpha // 255, g2 * alpha // 255, b2 * alpha // 255),
            )

        # Vignette
        vig  = Image.new("RGB", (W, H), (0, 0, 0))
        mask = Image.new("L",   (W, H), 0)
        mask_draw = ImageDraw.Draw(mask)
        for margin in range(120, 0, -10):
            alpha = int(90 * (1 - margin / 120))
            mask_draw.rectangle(
                [(W // 2 - margin * 3, H // 2 - margin * 5),
                 (W // 2 + margin * 3, H // 2 + margin * 5)],
                fill=alpha,
            )
        blurred_mask = mask.filter(ImageFilter.GaussianBlur(60))
        img.paste(vig, mask=blurred_mask)

        return img

    # ── Ken Burns Effect ──────────────────────────────────────────────────────

    def _ken_burns(
        self,
        img_array: np.ndarray,
        duration: float,
        fps: int = FPS,
        zoom: float = 1.10,
        direction: str = "zoom_in",
    ):
        """
        지연 계산(lazy) Ken Burns 효과 — 메모리 절약형.
        LANCZOS 대신 BILINEAR를 사용해 인코딩 속도를 높임.
        """
        h, w = img_array.shape[:2]
        src  = Image.fromarray(img_array)  # PIL 이미지로 한 번만 변환

        def make_frame(t: float) -> np.ndarray:
            t_norm = max(0.0, min(t / max(duration, 0.001), 1.0))

            if direction == "zoom_in":
                scale = 1.0 + (zoom - 1.0) * t_norm
            elif direction == "zoom_out":
                scale = zoom - (zoom - 1.0) * t_norm
            else:
                scale = zoom

            cw = max(1, int(w / scale))
            ch = max(1, int(h / scale))

            if direction == "pan_right":
                ox = int(max(0, w - cw) * t_norm)
                oy = (h - ch) // 2
            elif direction == "pan_left":
                ox = int(max(0, w - cw) * (1.0 - t_norm))
                oy = (h - ch) // 2
            else:
                ox = (w - cw) // 2
                oy = (h - ch) // 2

            ox = max(0, min(ox, w - cw))
            oy = max(0, min(oy, h - ch))

            cropped = src.crop((ox, oy, ox + cw, oy + ch))
            return np.array(cropped.resize((W, H), Image.BILINEAR))

        return VideoClip(make_frame, duration=duration)

    # ── URL → Clip ────────────────────────────────────────────────────────────

    def _url_to_clip(self, url: str, target_duration: float):
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(r.content)
        tmp.close()

        clip = VideoFileClip(tmp.name)
        # Resize to portrait if needed
        if clip.size != (W, H):
            clip = clip.resized((W, H))

        if clip.duration < target_duration:
            loops = int(np.ceil(target_duration / clip.duration))
            clip  = concatenate_videoclips([clip] * loops)
        return clip.subclipped(0, target_duration)

    # ── Text Overlays ─────────────────────────────────────────────────────────

    def _build_text_overlays(
        self,
        text: str,
        subtext: str,
        duration: float,
        is_hook: bool,
        is_cta: bool,
        fmt: str,
        script,
        scene,
    ) -> list:
        overlays = []
        accent   = self._accent_rgb(scene, fmt)

        # Stat (hook only)
        if is_hook:
            stat = (script.first_frame or {}).get("stat", "")
            if stat:
                stat_color = (0, 230, 118) if (script.first_frame or {}).get("color") == "green" \
                             else (255, 82, 82)
                stat_img = self._text_img(stat, size=88, bold=True, color=stat_color,
                                          glow=stat_color, max_w=W - 80)
                overlays.append(
                    self._overlay(stat_img, y_center=H * 0.27, dur=duration, fade_in=0.2)
                )

        # Main text
        if text:
            main_size = 54 if is_hook else (44 if is_cta else 42)
            main_img  = self._text_img(
                text, size=main_size, bold=True,
                color=(255, 255, 255), glow=accent,
                max_w=W - 100,
            )
            y_center = H * 0.46 if is_hook else (H * 0.48 if not is_cta else H * 0.42)
            overlays.append(
                self._overlay(main_img, y_center=y_center, dur=duration, fade_in=0.3)
            )

        # Subtext
        if subtext and subtext.strip():
            sub_img = self._text_img(
                subtext, size=28, bold=False,
                color=accent, max_w=W - 120,
            )
            sub_y = H * 0.63 if is_hook else H * 0.66
            overlays.append(
                self._overlay(sub_img, y_center=sub_y, dur=duration, fade_in=0.5)
            )

        # Scene label badge (non-hook scenes)
        if scene and getattr(scene, 'label', ''):
            badge_img = self._badge_img(scene.label, accent)
            bc = (
                ImageClip(badge_img)
                .with_position((28, 62))
                .with_duration(duration)
            )
            try:
                bc = bc.with_effects([mvfx.FadeIn(0.3)])
            except Exception:
                pass
            overlays.append(bc)

        # Hashtags (CTA)
        if is_cta and getattr(script, 'hashtags', []):
            tag_text = "  ".join(script.hashtags[:4])
            tag_img  = self._text_img(tag_text, size=24, bold=False,
                                      color=(120, 120, 180), max_w=W - 80)
            overlays.append(
                self._overlay(tag_img, y_center=H * 0.74, dur=duration, fade_in=0.7)
            )

        return overlays

    def _overlay(self, img_array: np.ndarray, y_center: float, dur: float, fade_in: float = 0.3):
        h = img_array.shape[0]
        clip = (
            ImageClip(img_array)
            .with_position(("center", max(0, int(y_center - h // 2))))
            .with_duration(dur)
        )
        try:
            clip = clip.with_effects([mvfx.FadeIn(fade_in)])
        except Exception:
            pass
        return clip

    # ── Text Image Rendering ──────────────────────────────────────────────────

    def _text_img(
        self,
        text: str,
        size: int,
        bold: bool,
        color: tuple,
        max_w: int = W - 80,
        glow: tuple | None = None,
    ) -> np.ndarray:
        font  = self._font(size, bold)
        lines = self._wrap(text, font, max_w)
        lh    = size + 12
        img_w = max_w + 20
        img_h = lh * len(lines) + 24

        base = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(base)

        y = 12
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw   = bbox[2] - bbox[0]
            x    = (img_w - tw) // 2

            # Glow halo
            if glow:
                gr, gg, gb = glow
                glow_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
                gd = ImageDraw.Draw(glow_layer)
                for dx in range(-4, 5):
                    for dy in range(-4, 5):
                        if dx * dx + dy * dy <= 16:
                            gd.text((x + dx, y + dy), line, font=font,
                                    fill=(gr, gg, gb, 55))
                glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(3))
                base = Image.alpha_composite(base, glow_layer)
                draw = ImageDraw.Draw(base)

            # Drop shadow (multi-pass)
            for sdx, sdy, salpha in [(2, 2, 200), (3, 3, 140), (1, 1, 160)]:
                draw.text((x + sdx, y + sdy), line, font=font, fill=(0, 0, 0, salpha))

            # Main text
            r2, g2, b2 = color
            draw.text((x, y), line, font=font, fill=(r2, g2, b2, 255))
            y += lh

        return np.array(base)

    def _badge_img(self, label: str, accent: tuple) -> np.ndarray:
        font  = self._font(26, bold=True)
        dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bbox  = dummy.textbbox((0, 0), label, font=font)
        tw    = bbox[2] - bbox[0]
        bw, bh = tw + 30, 38

        img  = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        r, g, b = accent
        draw.rounded_rectangle([(0, 0), (bw, bh)], radius=9, fill=(r, g, b, 220))
        ty = (bh - (bbox[3] - bbox[1])) // 2
        draw.text((15, ty), label, font=font, fill=(0, 0, 0, 255))
        return np.array(img)

    # ── Audio ─────────────────────────────────────────────────────────────────

    def _mix_audio(self, video_clip, script):
        audio_clips = []

        tts_path = self._gen_tts(script) if _TTS_OK else None
        if tts_path and os.path.exists(tts_path):
            try:
                tts = AudioFileClip(tts_path).with_volume_scaled(0.82)
                if tts.duration > video_clip.duration:
                    tts = tts.subclipped(0, video_clip.duration)
                audio_clips.append(tts)
            except Exception as e:
                print(f"      ⚠️  TTS 오디오 실패: {e}")

        music_path = self._gen_ambient_music(video_clip.duration)
        if music_path and os.path.exists(music_path):
            try:
                music = AudioFileClip(music_path).with_volume_scaled(0.12)
                if music.duration < video_clip.duration:
                    from moviepy import concatenate_audioclips
                    loops = int(np.ceil(video_clip.duration / music.duration))
                    music = concatenate_audioclips([music] * loops)
                music = music.subclipped(0, video_clip.duration)
                audio_clips.append(music)
            except Exception as e:
                print(f"      ⚠️  배경음악 실패: {e}")

        if audio_clips:
            try:
                combined = CompositeAudioClip(audio_clips)
                return video_clip.with_audio(combined)
            except Exception as e:
                print(f"      ⚠️  오디오 합성 실패: {e}")
        return video_clip

    # TTS ─────────────────────────────────────────────────────────────────────

    def _gen_tts(self, script) -> Optional[str]:
        lines: list[str] = [script.hook_text]
        for s in (script.scenes or []):
            if getattr(s, 'dialogue', ''):
                lines.append(s.dialogue)
        lines.append(getattr(script, 'cta_text', ''))
        full_text = "... ".join(filter(None, lines))[:3000]

        # 한국어 비율로 voice 선택
        kr_count = sum(1 for c in full_text if '가' <= c <= '힣')
        voice    = "ko-KR-InJoonNeural" if kr_count > len(full_text) * 0.2 else "en-US-GuyNeural"

        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp.close()
            _run_in_thread(edge_tts.Communicate(full_text, voice).save(tmp.name))
            return tmp.name
        except Exception as e:
            print(f"      ⚠️  TTS 실패: {e}")
            return None

    # Ambient Music ───────────────────────────────────────────────────────────

    def _gen_ambient_music(self, duration: float) -> Optional[str]:
        try:
            sr       = 44100
            n_frames = int(sr * (duration + 4))
            t        = np.linspace(0, duration + 4, n_frames, dtype=np.float32)

            # Low cinematic drone: fundamental + harmonics
            wave_data  = 0.18 * np.sin(2 * np.pi * 55.0  * t)
            wave_data += 0.10 * np.sin(2 * np.pi * 110.0 * t)
            wave_data += 0.07 * np.sin(2 * np.pi * 165.0 * t)
            wave_data += 0.05 * np.sin(2 * np.pi * 82.4  * t)
            # Subtle pulse
            lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.15 * t)
            wave_data *= lfo

            # Fade in/out
            fade = min(sr * 2, n_frames // 4)
            wave_data[:fade]  *= np.linspace(0.0, 1.0, fade)
            wave_data[-fade:] *= np.linspace(1.0, 0.0, fade)

            # Convert to 16-bit PCM
            wave_data = np.clip(wave_data, -1, 1)
            pcm = (wave_data * 32767).astype(np.int16)

            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            with wave.open(tmp.name, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(pcm.tobytes())
            return tmp.name
        except Exception as e:
            print(f"      ⚠️  Ambient music 실패: {e}")
            return None

    # ── Transitions ───────────────────────────────────────────────────────────

    def _apply_crossfades(self, clips: list) -> list:
        if len(clips) <= 1:
            return clips
        result = []
        for i, clip in enumerate(clips):
            try:
                effects = []
                if i > 0:
                    effects.append(mvfx.FadeIn(0.35))
                if i < len(clips) - 1:
                    effects.append(mvfx.FadeOut(0.35))
                if effects:
                    clip = clip.with_effects(effects)
            except Exception:
                pass
            result.append(clip)
        return result

    # ── Prompt Engineering ────────────────────────────────────────────────────

    def _build_prompt(self, scene, script, fmt: str, for_video: bool = False) -> str:
        parts: list[str] = []

        vn = getattr(scene, 'visual_note', '') or ''
        if vn in _VISUAL_NOTE_PROMPTS:
            parts.append(_VISUAL_NOTE_PROMPTS[vn])
        elif fmt in _FORMAT_PROMPTS:
            parts.append(_FORMAT_PROMPTS[fmt])

        for ck in ("green", "red", "yellow", "blue", "white"):
            if ck in vn:
                parts.append(_COLOR_PROMPTS[ck])
                break
        else:
            color = (getattr(script, 'first_frame', None) or {}).get("color", "blue")
            parts.append(_COLOR_PROMPTS.get(color, ""))

        parts.append("Korean financial market, luxury premium aesthetic, ")

        if for_video:
            parts.append("slow cinematic camera drift, atmospheric haze, ")

        parts.append(_QUALITY)
        parts.append(", portrait 9:16, no text, no watermarks, no people faces")
        return "".join(parts)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _accent_rgb(self, scene, fmt: str, dim: bool = False) -> tuple:
        vn = getattr(scene, 'visual_note', '') or ''
        color_map = {
            "green":  (0, 210, 100),
            "red":    (230, 60, 60),
            "yellow": (240, 190, 0),
            "blue":   (80, 130, 240),
            "white":  (200, 200, 220),
        }
        fmt_map = {
            "news_parody":    (200, 30, 30),
            "drama_twist":    (230, 180, 0),
            "celeb_collab":   (80, 130, 240),
            "meme_sequence":  (230, 180, 0),
            "pov":            (0, 210, 100),
            "character_skit": (80, 130, 240),
        }
        for ck, cv in color_map.items():
            if ck in vn:
                c = cv
                break
        else:
            c = fmt_map.get(fmt, (100, 100, 200))
        if dim:
            return (c[0] // 3, c[1] // 3, c[2] // 3)
        return c

    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        path = self.font_bold if bold else self.font_regular
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()

    def _wrap(self, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
        dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        words = str(text).split()
        lines: list[str] = []
        cur   = ""
        for word in words:
            test = (cur + " " + word).strip()
            bbox = dummy.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_w and cur:
                lines.append(cur)
                cur = word
            else:
                cur = test
        if cur:
            lines.append(cur)
        return lines or [""]


# ── Async helper (thread-safe) ────────────────────────────────────────────────

def _run_in_thread(coro) -> None:
    """이미 실행 중인 이벤트 루프가 있어도 async 코루틴 실행."""
    exc: list[Exception] = []

    def _worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        except Exception as e:
            exc.append(e)
        finally:
            loop.close()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=90)
    if exc:
        raise exc[0]