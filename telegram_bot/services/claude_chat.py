from __future__ import annotations

from anthropic import Anthropic

_MODEL = "claude-sonnet-4-20250514"
_MAX_HISTORY = 20


class ClaudeChat:
    """사용자별 대화 상태를 유지하는 Claude AI 래퍼."""

    def __init__(self, api_key: str) -> None:
        self.client   = Anthropic(api_key=api_key)
        self._history: dict[int, list[dict]] = {}

    async def reply(self, user_id: int, message: str) -> str:
        history = self._history.setdefault(user_id, [])
        history.append({"role": "user", "content": message})

        try:
            resp = self.client.messages.create(
                model=_MODEL,
                max_tokens=2000,
                messages=history,
            )
            answer = resp.content[0].text
        except Exception as e:
            return f"오류: {e}"

        history.append({"role": "assistant", "content": answer})

        # 최근 N개만 유지
        if len(history) > _MAX_HISTORY:
            self._history[user_id] = history[-_MAX_HISTORY:]

        return answer

    def clear(self, user_id: int) -> None:
        self._history.pop(user_id, None)
