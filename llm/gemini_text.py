"""파이프라인 분석기(시장 분석·숏폼 대본·리포트 요약)용 Gemini 텍스트 생성.

기본 모델은 CONFIG["gemini_model"](gemini-3.8-flash)이고, 과부하(503) 등으로 실패하면
CONFIG["gemini_fallback_models"] 순서대로 다시 시도합니다. 무료 티어라 예산 장부는 쓰지 않습니다.
"""
from __future__ import annotations

import logging

from llm.providers import GeminiProvider

logger = logging.getLogger(__name__)


class GeminiText:
    def __init__(self, config: dict, temperature: float | None = None) -> None:
        self.models = [config.get("gemini_model") or "gemini-3.8-flash",
                       *(config.get("gemini_fallback_models") or [])]
        self.temperature = temperature
        self._provider = GeminiProvider()

    @property
    def model(self) -> str:
        return self.models[0]

    def generate(self, prompt: str, max_output_tokens: int = 3000) -> str:
        max_output_tokens = max(max_output_tokens, 8000)   # Gemini 3.x 생각 토큰 포함
        """성공한 첫 모델의 답을 돌려줍니다. 모두 실패하면 마지막 오류를 올립니다."""
        last: Exception | None = None
        for model in dict.fromkeys(self.models):   # 중복 제거, 순서 유지
            try:
                text, _ = self._provider.generate(model, prompt, None, max_output_tokens,
                                                  temperature=self.temperature)
                return text
            except Exception as e:  # noqa: BLE001 — 다음 모델로 대체
                logger.warning("Gemini %s 실패: %s", model, e)
                last = e
        raise last or RuntimeError("Gemini 모델이 설정되지 않았습니다")
