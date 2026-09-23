"""멀티 모델 챗봇: 간단한 대화는 Gemini(무료), 종목 분석은 GPT-6 Astra."""
from __future__ import annotations

import asyncio
import json
import re

from invest import pepper_results
from invest.prompts import ANALYST, CHAT, CLASSIFY
from llm.router import LLMResult, ModelRouter

_MAX_HISTORY = 12
_ANALYSIS_WORDS = re.compile(r"분석|적정가|밸류|가치평가|점수|매수|매도|PEG|ROE|손절|버핏|린치|피셔|미너비니")


class RouterChat:
    def __init__(self, router: ModelRouter, results_path: str) -> None:
        self.router = router
        self.results_path = results_path
        self._history: dict[int, list[tuple[str, str]]] = {}

    def clear(self, user_id: int) -> None:
        self._history.pop(user_id, None)

    def _intent(self, message: str, tickers: list[str]) -> str:
        if tickers and _ANALYSIS_WORDS.search(message):
            return "analysis"
        if not tickers:
            return "chat"
        r = self.router.run("classify_intent", message, system=CLASSIFY)
        return "analysis" if r.ok and "analysis" in r.text.lower() else "chat"

    def analyze(self, ticker: str, question: str = "") -> LLMResult:
        results = pepper_results.load(self.results_path)
        if not results or ticker not in results.get("tickers", {}):
            return LLMResult(text=f"{ticker}의 Pepper 결과가 없습니다. 먼저 pepper score를 실행하세요.",
                             task="stock_analysis", tier="none")
        data = pepper_results.compact(ticker, results["tickers"][ticker])
        prompt = (f"기준일: {results.get('asof')}\n규칙 버전: {json.dumps(results.get('rules_version'), ensure_ascii=False)}\n"
                  f"Pepper 결과:\n{json.dumps(data, ensure_ascii=False)}\n\n질문: {question or '4대가 관점으로 점검해줘'}")
        return self.router.run("stock_analysis", prompt, system=ANALYST)

    def _reply_sync(self, user_id: int, message: str) -> str:
        results = pepper_results.load(self.results_path)
        tickers = pepper_results.find_tickers(message, results)
        if self._intent(message, tickers) == "analysis" and tickers:
            r = self.analyze(tickers[0], message)
        else:
            history = self._history.get(user_id, [])
            context = "\n".join(f"{'사용자' if role == 'user' else 'Edgar'}: {text}" for role, text in history)
            r = self.router.run("chat_general", f"{context}\n사용자: {message}".strip(), system=CHAT)
        answer = r.text
        if r.ok:
            answer += f"\n\n— {r.model}" + (f" · ${r.cost_usd:.3f}" if r.cost_usd else " · 무료")
            if r.downgraded:
                answer += " (대체 모델)"
        h = self._history.setdefault(user_id, [])
        h += [("user", message), ("assistant", r.text)]
        self._history[user_id] = h[-_MAX_HISTORY:]
        return answer

    async def reply(self, user_id: int, message: str) -> str:
        return await asyncio.to_thread(self._reply_sync, user_id, message)
