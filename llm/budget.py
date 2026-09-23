"""유료 모델 사용액 장부와 월 예산 가드.

- 호출 전: 최악의 경우 비용(입력 추정 + max_output_tokens 전부)을 계산해
  이번 달 사용액 + 예상액이 상한을 넘으면 호출하지 않습니다.
- 호출 후: 실제 usage로 비용을 계산해 CSV 장부에 한 줄 기록합니다.
월 구분은 OpenAI 청구와 같은 UTC 기준입니다.
"""
from __future__ import annotations

import csv
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ["time_utc", "task", "provider", "model", "input_tokens", "cached_tokens", "output_tokens", "cost_usd"]


@dataclass
class Usage:
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0


def cost_usd(pricing: dict, model: str, usage: Usage) -> float:
    p = pricing.get(model)
    if p is None:
        raise KeyError(f"models.yaml pricing에 {model} 가격이 없습니다")
    uncached = max(0, usage.input_tokens - usage.cached_tokens)
    return (uncached * p["input"] + usage.cached_tokens * p.get("cached_input", p["input"])
            + usage.output_tokens * p["output"]) / 1_000_000


class BudgetLedger:
    def __init__(self, path: str | Path, monthly_limit: float, soft_ratio: float = 0.8, now=None) -> None:
        self.path = Path(path)
        self.limit = float(monthly_limit)
        self.soft_ratio = soft_ratio
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()
        self._reserved = 0.0

    def _month(self) -> str:
        return self._now().strftime("%Y-%m")

    def spent_this_month(self) -> float:
        if not self.path.exists():
            return 0.0
        month, total = self._month(), 0.0
        with self.path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["time_utc"].startswith(month):
                    total += float(row["cost_usd"])
        return total

    def remaining(self) -> float:
        return self.limit - self.spent_this_month() - self._reserved

    def is_soft_limited(self) -> bool:
        return self.spent_this_month() >= self.limit * self.soft_ratio

    def reserve(self, worst_case: float) -> bool:
        """예상 최대 비용을 잡아둡니다. 상한을 넘으면 False."""
        with self._lock:
            if worst_case > self.remaining():
                return False
            self._reserved += worst_case
            return True

    def settle(self, worst_case: float, task: str, provider: str, model: str, usage: Usage, cost: float) -> None:
        with self._lock:
            self._reserved = max(0.0, self._reserved - worst_case)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            new = not self.path.exists()
            with self.path.open("a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS)
                if new:
                    w.writeheader()
                w.writerow({"time_utc": self._now().strftime("%Y-%m-%dT%H:%M:%SZ"), "task": task,
                            "provider": provider, "model": model, "input_tokens": usage.input_tokens,
                            "cached_tokens": usage.cached_tokens, "output_tokens": usage.output_tokens,
                            "cost_usd": f"{cost:.6f}"})

    def release(self, worst_case: float) -> None:
        with self._lock:
            self._reserved = max(0.0, self._reserved - worst_case)

    def status(self) -> dict:
        spent = self.spent_this_month()
        return {"month": self._month(), "spent_usd": round(spent, 4), "limit_usd": self.limit,
                "remaining_usd": round(self.limit - spent, 4), "soft_limited": spent >= self.limit * self.soft_ratio}
