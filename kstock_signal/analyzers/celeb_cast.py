from __future__ import annotations

import copy
import re
from dataclasses import dataclass


@dataclass
class CelebCharacter:
    name:        str    # "Elon Musk"
    company:     str    # "Tesla"
    role:        str    # "CEO, Tesla Inc."
    avatar_id:   str    # HeyGen avatar ID (비어있으면 텍스트 전용 모드)
    voice_id:    str    # HeyGen voice ID
    nationality: str    # "American" | "Korean"
    emoji:       str    # "🚀"
    text_color:  str = "green"   # green | blue | yellow | white | gray
    side:        str = "left"    # left | right (split-screen 배치용)


# ── 기업명 키워드 → CEO 캐릭터 매핑 ─────────────────────────────────────────
# avatar_id / voice_id 는 HeyGen 콘솔에서 발급 후 채워 넣으세요.
# (공란이면 PIL 텍스트 전용 렌더러로 fallback)

_CELEB_DB: list[tuple[list[str], CelebCharacter]] = [
    (
        ["테슬라", "tesla"],
        CelebCharacter(
            name="Elon Musk", company="Tesla", role="CEO, Tesla Inc.",
            avatar_id="", voice_id="en-US-GuyNeural",
            nationality="American", emoji="🚀", text_color="green",
        ),
    ),
    (
        ["삼성전자", "삼성", "samsung electronics", "samsung"],
        CelebCharacter(
            name="Jay Y. Lee", company="Samsung Electronics",
            role="Chairman, Samsung Group",
            avatar_id="", voice_id="ko-KR-InJoonNeural",
            nationality="Korean", emoji="💎", text_color="blue",
        ),
    ),
    (
        ["애플", "apple"],
        CelebCharacter(
            name="Tim Cook", company="Apple Inc.", role="CEO, Apple",
            avatar_id="", voice_id="en-US-GuyNeural",
            nationality="American", emoji="🍎", text_color="white",
        ),
    ),
    (
        ["엔비디아", "nvidia"],
        CelebCharacter(
            name="Jensen Huang", company="NVIDIA", role="CEO, NVIDIA",
            avatar_id="", voice_id="en-US-GuyNeural",
            nationality="American", emoji="🖥️", text_color="green",
        ),
    ),
    (
        ["현대자동차", "현대차", "현대", "hyundai"],
        CelebCharacter(
            name="Euisun Chung", company="Hyundai Motor Group",
            role="Chairman, Hyundai Motor Group",
            avatar_id="", voice_id="ko-KR-InJoonNeural",
            nationality="Korean", emoji="🚗", text_color="white",
        ),
    ),
    (
        ["sk하이닉스", "sk hynix"],
        CelebCharacter(
            name="Kwak Noh-jung", company="SK Hynix", role="CEO, SK Hynix",
            avatar_id="", voice_id="ko-KR-InJoonNeural",
            nationality="Korean", emoji="💾", text_color="yellow",
        ),
    ),
    (
        ["lg전자", "lg electronics"],
        CelebCharacter(
            name="William Cho", company="LG Electronics",
            role="CEO, LG Electronics",
            avatar_id="", voice_id="ko-KR-InJoonNeural",
            nationality="Korean", emoji="📺", text_color="white",
        ),
    ),
    (
        ["카카오"],
        CelebCharacter(
            name="Kakao Chairman", company="Kakao Corp.", role="Kakao Group",
            avatar_id="", voice_id="ko-KR-InJoonNeural",
            nationality="Korean", emoji="🟡", text_color="yellow",
        ),
    ),
    (
        ["포스코", "posco"],
        CelebCharacter(
            name="POSCO CEO", company="POSCO Holdings",
            role="CEO, POSCO Holdings",
            avatar_id="", voice_id="ko-KR-InJoonNeural",
            nationality="Korean", emoji="⚙️", text_color="gray",
        ),
    ),
    (
        ["셀트리온"],
        CelebCharacter(
            name="Seo Jung-jin", company="Celltrion",
            role="Chairman, Celltrion Group",
            avatar_id="", voice_id="ko-KR-InJoonNeural",
            nationality="Korean", emoji="💊", text_color="white",
        ),
    ),
    (
        ["배터리", "lg에너지", "lg energy"],
        CelebCharacter(
            name="Kim Dong-myung", company="LG Energy Solution",
            role="CEO, LG Energy Solution",
            avatar_id="", voice_id="ko-KR-InJoonNeural",
            nationality="Korean", emoji="🔋", text_color="green",
        ),
    ),
    (
        ["한화", "hanwha"],
        CelebCharacter(
            name="Kim Seung-youn", company="Hanwha Group",
            role="Chairman, Hanwha Group",
            avatar_id="", voice_id="ko-KR-InJoonNeural",
            nationality="Korean", emoji="💥", text_color="red",
        ),
    ),
    (
        ["네이버", "naver"],
        CelebCharacter(
            name="Choi Soo-yeon", company="NAVER", role="CEO, NAVER Corp.",
            avatar_id="", voice_id="ko-KR-InJoonNeural",
            nationality="Korean", emoji="🔍", text_color="green",
        ),
    ),
]

# ── Fallback 캐릭터 풀 ────────────────────────────────────────────────────────
# 매칭이 안 될 때 상황에 맞게 배정할 보완 캐릭터 목록

_FALLBACK_AMERICAN = CelebCharacter(
    name="Warren Buffett", company="Berkshire Hathaway",
    role="CEO, Berkshire Hathaway",
    avatar_id="", voice_id="en-US-GuyNeural",
    nationality="American", emoji="💰", text_color="yellow",
    side="right",
)

_FALLBACK_KOREAN_CEO = CelebCharacter(
    name="Korean CEO", company="Korean Corp.",
    role="CEO, Korean Corp.",
    avatar_id="", voice_id="ko-KR-InJoonNeural",
    nationality="Korean", emoji="🏢", text_color="white",
    side="left",
)

_FALLBACK_HEDGE_FUND = CelebCharacter(
    name="Ray Dalio", company="Bridgewater Associates",
    role="Founder, Bridgewater Associates",
    avatar_id="", voice_id="en-US-GuyNeural",
    nationality="American", emoji="📈", text_color="green",
    side="right",
)


class CelebCaster:
    """
    리포트 텍스트에서 기업명을 감지해 유명인 캐릭터 2명을 캐스팅.

    규칙:
    - 키워드 매칭 → 해당 CEO 직접 배정
    - 1명만 발견 → Warren Buffett / Ray Dalio로 보완
    - 아무도 없음 → 종목명으로 상징적 캐릭터 생성 (항상 2명 반환)
      예: '삼성전자' → Jay Y. Lee + Warren Buffett
          미지 종목 → Korean CEO + Ray Dalio (스토리용 구도 형성)
    """

    def cast(self, report: dict) -> list[CelebCharacter]:
        stock_name = report.get("stock_name", "")
        text = (
            report.get("title", "") + " " + report.get("text", "") + " " + stock_name
        ).lower()

        found: list[CelebCharacter] = []
        seen: set[str] = set()

        # 1차: 키워드 매칭
        for keywords, celeb in _CELEB_DB:
            if celeb.name in seen:
                continue
            for kw in keywords:
                if kw in text:
                    c = copy.copy(celeb)
                    c.side = "left" if not found else "right"
                    found.append(c)
                    seen.add(celeb.name)
                    break
            if len(found) >= 2:
                break

        # 2차: 1명만 발견 → 반대쪽 글로벌 인물 보완
        if len(found) == 1:
            existing_nationality = found[0].nationality
            if existing_nationality == "Korean":
                # 한국 CEO 발견 → 미국 투자자 추가
                fb = copy.copy(_FALLBACK_AMERICAN)
            else:
                # 미국 CEO 발견 → 한국 투자 구도
                fb = copy.copy(_FALLBACK_KOREAN_CEO)
                fb.name = f"{stock_name} CEO" if stock_name else fb.name
                fb.company = stock_name if stock_name else fb.company
                fb.role = f"CEO, {stock_name}" if stock_name else fb.role
            fb.side = "right"
            found.append(fb)

        # 3차: 아무도 없음 → 종목명 기반 상징적 캐릭터 2명 생성
        if not found:
            # 한국어 종목명이면 한국 CEO vs 미국 투자자 구도
            is_korean = any('가' <= c <= '힣' for c in stock_name)
            if is_korean:
                ceo = copy.copy(_FALLBACK_KOREAN_CEO)
                ceo.name = f"{stock_name} 대표이사"
                ceo.company = stock_name
                ceo.role = f"대표이사, {stock_name}"
                ceo.side = "left"
                found.append(ceo)
                inv = copy.copy(_FALLBACK_AMERICAN)
                inv.side = "right"
                found.append(inv)
            else:
                # 영문 종목명이면 미국 CEO vs 글로벌 투자자 구도
                ceo = copy.copy(_FALLBACK_HEDGE_FUND)
                ceo.side = "left"
                found.append(ceo)
                inv = copy.copy(_FALLBACK_AMERICAN)
                inv.side = "right"
                found.append(inv)

        return found[:2]
