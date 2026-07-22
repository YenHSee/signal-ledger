import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from core.llm_factory import ModelSpec, ModelTier, get_llm  # noqa: E402
from core.report_generation import (  # noqa: E402
    build_analysis_prompt,
    generate_investment_analysis,
    normalize_provider_metadata,
)


class FakeExecutor:
    def __init__(self, message):
        self.message = message

    def invoke(self, _payload):
        return {"messages": [self.message]}


class FakeParser:
    def parse(self, content):
        return SimpleNamespace(model_dump=lambda: json.loads(content))


class ReportGenerationTests(unittest.TestCase):
    def test_prompt_prohibits_cross_period_ratios_and_requires_target_formula(self):
        prompt = build_analysis_prompt(
            "NVDA",
            datetime(2026, 1, 9, 21, tzinfo=timezone.utc),
            {"smart_money_consensus": {"current_price": 100}},
        )
        self.assertIn("do not divide YTD free cash flow by annual revenue", prompt)
        self.assertIn("forward EPS × exit P/E = target", prompt)

    def test_ollama_uses_native_json_mode(self):
        llm = get_llm(
            tier=ModelTier.LOCAL,
            spec=ModelSpec("ollama", ModelTier.LOCAL, "qwen2.5:7b"),
        )
        self.assertEqual(llm.format, "json")

    def _message(self, provider):
        if provider == "ollama":
            response = {
                "model": "qwen2.5:7b",
                "done_reason": "stop",
            }
            usage = {"input_tokens": 100, "output_tokens": 40, "total_tokens": 140}
        else:
            response = {
                "model_name": "deepseek-v4-pro" if provider == "deepseek" else "gpt-4o",
                "finish_reason": "stop",
                "system_fingerprint": "fp_test",
                "token_usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 40,
                    "total_tokens": 140,
                },
            }
            usage = None
        content = json.dumps({
            "conclusion": "HOLD",
            "conviction_level": "Medium",
            "target_price": "275",
            "upside_downside_pct": "+6.0%",
            "reasoning": "Evidence-based summary.",
            "risk_level": "Medium",
            "full_report": "# Equity Research Report",
        })
        return SimpleNamespace(
            content=content,
            response_metadata=response,
            usage_metadata=usage,
        )

    def test_normalizes_deepseek_openai_and_ollama_usage(self):
        cases = (
            ("deepseek", ModelTier.NORMAL, "deepseek-v4-pro", None),
            ("openai", ModelTier.SMART, "gpt-4o", None),
            ("ollama", ModelTier.LOCAL, "qwen2.5:7b", "sha256:test"),
        )
        for provider, tier, model, digest in cases:
            with self.subTest(provider=provider):
                spec = ModelSpec(provider, tier, model)
                result = normalize_provider_metadata(self._message(provider), spec, digest)
                self.assertEqual(result["response_model"], model)
                self.assertEqual(result["finish_reason"], "stop")
                self.assertEqual(result["usage"]["total_tokens"], 140)
                self.assertEqual(result["local_model_digest"], digest)

    def test_single_agent_envelope_links_final_run_and_aggregate(self):
        spec = ModelSpec("deepseek", ModelTier.NORMAL, "deepseek-v4-pro")
        report = generate_investment_analysis(
            "AAPL",
            {
                "smart_money_consensus": {
                    "current_price": 259.37,
                    "price_trade_date": "2026-01-09",
                },
                "recent_catalysts": [{"finnhub_id": 123}],
            },
            analysis_as_of=datetime(2026, 1, 9, 21, tzinfo=timezone.utc),
            generation_mode="historical_backfill",
            tier=ModelTier.NORMAL,
            model_spec=spec,
            executor=FakeExecutor(self._message("deepseek")),
            parser=FakeParser(),
            run_preflight=False,
        )
        metadata = report["generation_metadata"]
        run = metadata["agent_runs"][0]
        output = report["agent_outputs"][0]
        self.assertEqual(metadata["final_run_id"], run["run_id"])
        self.assertEqual(output["run_id"], run["run_id"])
        self.assertEqual(metadata["provenance_status"], "complete")
        self.assertEqual(metadata["aggregate_usage"]["total_tokens"], 140)
        self.assertEqual(report["target_price"], 275.0)
        self.assertEqual(report["upside_downside_pct"], "+6.0%")
        self.assertEqual(
            output["output"]["evidence_refs"],
            ["price:AAPL:2026-01-09", "news:AAPL:123"],
        )

    def test_canonicalizes_unambiguous_local_level_suffixes(self):
        message = self._message("ollama")
        payload = json.loads(message.content)
        payload["conviction_level"] = "Medium conviction"
        payload["risk_level"] = "High risk"
        message.content = json.dumps(payload)
        report = generate_investment_analysis(
            "AAPL",
            {"smart_money_consensus": {"current_price": 259.37}},
            analysis_as_of=datetime(2026, 1, 9, 21, tzinfo=timezone.utc),
            generation_mode="historical_backfill",
            tier=ModelTier.LOCAL,
            model_spec=ModelSpec("ollama", ModelTier.LOCAL, "qwen2.5:7b"),
            executor=FakeExecutor(message),
            parser=FakeParser(),
            run_preflight=False,
            local_model_digest="sha256:test",
        )
        self.assertEqual(report["conviction_level"], "Medium")
        self.assertEqual(report["risk_level"], "High")


if __name__ == "__main__":
    unittest.main()
