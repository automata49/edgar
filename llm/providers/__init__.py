"""모델 제공자 어댑터. 각 어댑터는 generate(...) -> (text, Usage)를 구현합니다."""
from __future__ import annotations

import os

from llm.budget import Usage


class ProviderError(RuntimeError):
    def __init__(self, message: str, usage: Usage | None = None) -> None:
        super().__init__(message)
        self.usage = usage   # 과금은 됐지만 답이 쓸모없을 때 비용 기록용


class GeminiProvider:
    """Google Gemini (무료 티어). 무료 티어 입력은 Google 제품 개선에 쓰일 수 있습니다."""

    name = "gemini"

    def __init__(self, api_key_env: str = "GEMINI_API_KEY") -> None:
        self.api_key = os.getenv(api_key_env)
        self._client = None

    def _get(self):
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY가 설정되지 않았습니다")
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate(self, model: str, prompt: str, system: str | None, max_output_tokens: int,
                 reasoning: str | None = None, json_schema: dict | None = None) -> tuple[str, Usage]:
        from google.genai import types
        cfg = {"system_instruction": system, "max_output_tokens": max_output_tokens}
        if json_schema:
            cfg.update(response_mime_type="application/json", response_json_schema=json_schema)
        try:
            resp = self._get().models.generate_content(model=model, contents=prompt,
                                                       config=types.GenerateContentConfig(**cfg))
        except ProviderError:
            raise
        except Exception as e:  # SDK 예외 종류가 많아 한 번에 감쌉니다
            raise ProviderError(f"Gemini 호출 실패: {e}") from e
        meta = getattr(resp, "usage_metadata", None)
        usage = Usage(getattr(meta, "prompt_token_count", 0) or 0, getattr(meta, "cached_content_token_count", 0) or 0,
                      getattr(meta, "candidates_token_count", 0) or 0)
        if not resp.text:
            raise ProviderError("Gemini 빈 응답")
        return resp.text, usage


class OpenAIProvider:
    """OpenAI Responses API (GPT-6 Astra)."""

    name = "openai"

    def __init__(self, api_key_env: str = "OPENAI_API_KEY") -> None:
        self.api_key = os.getenv(api_key_env)
        self._client = None

    def _get(self):
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY가 설정되지 않았습니다")
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate(self, model: str, prompt: str, system: str | None, max_output_tokens: int,
                 reasoning: str | None = None, json_schema: dict | None = None) -> tuple[str, Usage]:
        kwargs = {"model": model, "input": prompt, "instructions": system,
                  "max_output_tokens": max_output_tokens, "store": False}
        if reasoning:
            kwargs["reasoning"] = {"effort": reasoning}   # Astra는 none 미지원 → 최소 low
        if json_schema:
            kwargs["text"] = {"format": {"type": "json_schema", "name": "pepper_analysis",
                                         "schema": json_schema, "strict": True}}
        try:
            resp = self._get().responses.create(**kwargs)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"OpenAI 호출 실패: {e}") from e
        u = resp.usage
        cached = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
        usage = Usage(u.input_tokens, cached, u.output_tokens)
        text = resp.output_text or ""
        if getattr(resp, "status", None) == "incomplete":
            text += "\n\n(출력 토큰 한도에 도달해 답변이 잘렸을 수 있습니다)"
        if not text.strip():
            raise ProviderError("OpenAI 빈 응답 (추론에 출력 한도를 모두 사용)", usage)
        return text, usage


def build(name: str, spec: dict):
    if name == "gemini":
        return GeminiProvider(spec.get("api_key_env", "GEMINI_API_KEY"))
    if name == "openai":
        return OpenAIProvider(spec.get("api_key_env", "OPENAI_API_KEY"))
    raise ValueError(f"알 수 없는 provider: {name}")
