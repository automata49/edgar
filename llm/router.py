"""작업(task) → 모델 선택기.

사용법:
    router = ModelRouter.from_config("config/models.yaml")
    result = router.run("stock_analysis", prompt, system=SYSTEM)
    print(result.text, result.model, result.cost_usd)

규칙
- 무료 티어(Gemini)는 과금이 없어 예산 검사를 하지 않습니다.
- 유료 티어(Astra)는 호출 전 최악 비용을 예약하고, 월 상한을 넘으면 호출하지 않습니다.
- 사용액이 상한의 80%를 넘으면 reasoning을 low로 낮춰 비용을 줄입니다.
- 유료 호출이 막히거나 실패하면 fallback 티어(무료)로 내려갑니다.
  단, private 작업(보유·계좌 정보 포함)은 무료 티어로 보내지 않고 규칙 기반 안내만 돌려줍니다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from llm.budget import BudgetLedger, Usage, cost_usd
from llm.providers import ProviderError, build

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    text: str
    task: str
    tier: str
    provider: str | None = None
    model: str | None = None
    cost_usd: float = 0.0
    downgraded: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.provider is not None


class ModelRouter:
    def __init__(self, config: dict, providers: dict | None = None, ledger: BudgetLedger | None = None,
                 base_dir: str | Path = ".") -> None:
        self.config = config
        self.tiers = config["tiers"]
        self.tasks = config["tasks"]
        self.pricing = config.get("pricing", {})
        b = config.get("budget", {})
        self.chars_per_token = float(b.get("chars_per_token", 2.0))
        self.ledger = ledger or BudgetLedger(Path(base_dir) / b.get("ledger", "data/llm_usage.csv"),
                                             b.get("monthly_usd_limit", 20.0), b.get("soft_limit_ratio", 0.8))
        self.providers = providers or {n: build(n, s) for n, s in config.get("providers", {}).items()}
        self._validate()

    @classmethod
    def from_config(cls, path: str | Path, base_dir: str | Path | None = None) -> ModelRouter:
        path = Path(path)
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(cfg, base_dir=base_dir or path.resolve().parents[1])

    def _validate(self) -> None:
        for task, spec in self.tasks.items():
            if spec.get("tier") not in self.tiers:
                raise ValueError(f"models.yaml: {task}의 tier {spec.get('tier')!r} 없음")
        for name, tier in self.tiers.items():
            for m in tier.get("models", []):
                if tier.get("paid") and m["model"] not in self.pricing:
                    raise ValueError(f"models.yaml: 유료 모델 {m['model']} 가격 누락")
            fb = tier.get("fallback")
            if fb and (fb not in self.tiers or self.tiers[fb].get("paid")):
                raise ValueError(f"models.yaml: {name}.fallback은 무료 티어여야 합니다")

    # ── 비용 추정 ───────────────────────────────────────────
    def estimate_tokens(self, *texts: str | None) -> int:
        return int(sum(len(t or "") for t in texts) / self.chars_per_token) + 50

    def worst_case_cost(self, model: str, input_tokens: int, max_output_tokens: int) -> float:
        return cost_usd(self.pricing, model, Usage(input_tokens, 0, max_output_tokens))

    # ── 실행 ────────────────────────────────────────────────
    def run(self, task: str, prompt: str, system: str | None = None, json_schema: dict | None = None) -> LLMResult:
        spec = self.tasks.get(task)
        if spec is None:
            raise KeyError(f"models.yaml tasks에 {task!r} 없음")
        tier_name = spec["tier"]
        private = bool(spec.get("private"))
        result = self._run_tier(task, tier_name, prompt, system, json_schema)
        if result.ok:
            return result
        fb = self.tiers[tier_name].get("fallback")
        if fb and not private:
            down = self._run_tier(task, fb, prompt, system, json_schema)
            down.downgraded = True
            down.notes = result.notes + down.notes + [f"{tier_name} → {fb} 대체 모델로 답변"]
            if down.ok:
                return down
            result.notes = down.notes
        elif private:
            result.notes.append("보유·계좌 정보가 포함된 작업이라 무료 모델로 대체하지 않았습니다")
        result.text = "지금은 AI 해석을 만들 수 없습니다. Pepper 계산 결과만 확인해 주세요.\n(" + "; ".join(result.notes) + ")"
        return result

    def _run_tier(self, task: str, tier_name: str, prompt: str, system: str | None, schema: dict | None) -> LLMResult:
        tier = self.tiers[tier_name]
        out = LLMResult(text="", task=task, tier=tier_name)
        for m in tier.get("models", []):
            provider = self.providers.get(m["provider"])
            if provider is None:
                out.notes.append(f"{m['provider']} 미설정")
                continue
            reasoning = m.get("reasoning")
            reserved = 0.0
            if tier.get("paid"):
                if reasoning and reasoning != "low" and self.ledger.is_soft_limited():
                    reasoning = "low"
                    out.notes.append("월 예산 80% 초과 — reasoning low로 실행")
                reserved = self.worst_case_cost(m["model"], self.estimate_tokens(prompt, system), m["max_output_tokens"])
                if not self.ledger.reserve(reserved):
                    out.notes.append(f"월 예산 상한 ${self.ledger.limit:.0f} 도달 — {m['model']} 호출 안 함")
                    continue
            try:
                text, usage = provider.generate(m["model"], prompt, system, m["max_output_tokens"], reasoning, schema)
            except Exception as e:  # noqa: BLE001 — SDK 미설치 등 예상 밖 오류도 봇을 멈추지 않도록
                usage = getattr(e, "usage", None) if isinstance(e, ProviderError) else None
                if tier.get("paid"):
                    if usage:
                        self.ledger.settle(reserved, task, m["provider"], m["model"], usage,
                                           cost_usd(self.pricing, m["model"], usage))
                    else:
                        self.ledger.release(reserved)
                logger.warning("%s/%s 실패: %s", m["provider"], m["model"], e)
                out.notes.append(str(e))
                continue
            cost = cost_usd(self.pricing, m["model"], usage) if m["model"] in self.pricing else 0.0
            if tier.get("paid"):
                self.ledger.settle(reserved, task, m["provider"], m["model"], usage, cost)
            out.text, out.provider, out.model, out.cost_usd = text, m["provider"], m["model"], cost
            return out
        return out

    def budget_status(self) -> dict:
        return self.ledger.status()
