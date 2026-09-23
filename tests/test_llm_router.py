from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from llm.budget import BudgetLedger, Usage, cost_usd
from llm.providers import ProviderError
from llm.router import ModelRouter

CONFIG = yaml.safe_load((Path(__file__).resolve().parents[1] / "config/models.yaml").read_text(encoding="utf-8"))


class FakeProvider:
    def __init__(self, name, usage=None, fail=False, fail_usage=None):
        usage = usage or Usage(1000, 0, 500)
        self.name, self.usage, self.fail, self.fail_usage, self.calls = name, usage, fail, fail_usage, []

    def generate(self, model, prompt, system, max_output_tokens, reasoning=None, json_schema=None):
        self.calls.append({"model": model, "reasoning": reasoning, "max": max_output_tokens})
        if self.fail:
            raise ProviderError(f"{self.name} down", self.fail_usage)
        return f"{self.name}:{model}", self.usage


def make(tmp, spent=0.0, openai=None, gemini=None, limit=20.0):
    now = lambda: datetime(2026, 9, 23, tzinfo=timezone.utc)
    ledger = BudgetLedger(Path(tmp) / "usage.csv", limit, 0.8, now=now)
    if spent:
        ledger.settle(0, "seed", "openai", "gpt-6-astra", Usage(), spent)
    providers = {"openai": openai or FakeProvider("openai"), "gemini": gemini or FakeProvider("gemini")}
    return ModelRouter(CONFIG, providers=providers, ledger=ledger)


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_simple_tasks_use_free_gemini(self):
        r = make(self.tmp)
        for task in ("classify_intent", "format_message", "chat_general", "summarize_news"):
            res = r.run(task, "hi")
            self.assertEqual(res.provider, "gemini")
            self.assertEqual(res.cost_usd, 0.0)
        self.assertEqual(r.budget_status()["spent_usd"], 0.0)

    def test_analysis_uses_astra_and_records_cost(self):
        r = make(self.tmp)
        res = r.run("stock_analysis", "NVDA")
        self.assertEqual((res.provider, res.model), ("openai", "gpt-6-astra"))
        expected = (1000 * 10 + 500 * 50) / 1_000_000
        self.assertAlmostEqual(res.cost_usd, expected)
        self.assertAlmostEqual(r.budget_status()["spent_usd"], round(expected, 4))

    def test_cached_tokens_priced_lower(self):
        self.assertAlmostEqual(cost_usd(CONFIG["pricing"], "gpt-6-astra", Usage(1000, 800, 0)),
                               (200 * 10 + 800 * 1) / 1_000_000)

    def test_budget_cap_blocks_astra_and_falls_back_to_gemini(self):
        r = make(self.tmp, spent=19.99)
        res = r.run("stock_analysis", "NVDA")
        self.assertEqual(res.provider, "gemini")
        self.assertTrue(res.downgraded)
        self.assertEqual(r.providers["openai"].calls, [])
        self.assertLessEqual(r.budget_status()["spent_usd"], 20.0)

    def test_soft_limit_lowers_reasoning(self):
        r = make(self.tmp, spent=17.0)
        r.run("stock_analysis", "NVDA")
        self.assertEqual(r.providers["openai"].calls[0]["reasoning"], "low")

    def test_private_task_never_goes_to_free_tier(self):
        r = make(self.tmp, spent=20.0)
        res = r.run("portfolio_review", "보유 수량 ...")
        self.assertFalse(res.ok)
        self.assertEqual(r.providers["gemini"].calls, [])
        self.assertIn("Pepper 계산 결과", res.text)

    def test_provider_error_still_bills_consumed_tokens(self):
        r = make(self.tmp, openai=FakeProvider("openai", fail=True, fail_usage=Usage(1000, 0, 4000)))
        res = r.run("stock_analysis", "NVDA")
        self.assertEqual(res.provider, "gemini")
        self.assertAlmostEqual(r.budget_status()["spent_usd"], round((1000 * 10 + 4000 * 50) / 1e6, 4))

    def test_gemini_fallback_model_on_error(self):
        g = FakeProvider("gemini")
        calls = {"n": 0}
        orig = g.generate

        def flaky(model, *a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ProviderError("rate limit")
            return orig(model, *a, **k)
        g.generate = flaky
        res = make(self.tmp, gemini=g).run("chat_general", "hi")
        self.assertEqual(res.model, "gemini-3.6-flash")

    def test_worst_case_reservation(self):
        r = make(self.tmp)
        worst = r.worst_case_cost("gpt-6-astra", 20_000, 4_000)
        self.assertAlmostEqual(worst, 0.4)
        # $20 상한이면 최악 기준으로도 월 50회 분석 가능
        self.assertEqual(round(20 / worst), 50)

    def test_unexpected_error_releases_reservation(self):
        class Broken:
            def generate(self, *a, **k):
                raise ImportError("openai 미설치")
        r = make(self.tmp, openai=Broken())
        res = r.run("stock_analysis", "NVDA")
        self.assertEqual(res.provider, "gemini")
        self.assertEqual(r.ledger._reserved, 0.0)

    def test_config_rejects_paid_fallback(self):
        bad = yaml.safe_load(yaml.safe_dump(CONFIG))
        bad["tiers"]["analysis"]["fallback"] = "analysis"
        with self.assertRaises(ValueError):
            ModelRouter(bad, providers={}, ledger=BudgetLedger(Path(self.tmp) / "x.csv", 20))


if __name__ == "__main__":
    unittest.main()
