from collections import Counter
from datetime import date, timedelta
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from scripts.seed_sample_data import (  # noqa: E402
    DatasetValidationError,
    load_fixture,
)
from scripts.export_sample_news import (  # noqa: E402
    DEFAULT_REPORT_DATES,
    _headline_mentions_ticker,
)


FIXTURE_DIR = REPO_ROOT / "sample-data" / "v1"

class SampleFixtureTests(unittest.TestCase):
    def test_committed_draft_contains_fundamentals_and_2026_ytd_prices(self):
        manifest, data = load_fixture(FIXTURE_DIR, allow_draft=True)

        self.assertEqual(manifest["status"], "draft")
        self.assertEqual(len(manifest["tickers"]), 10)
        self.assertEqual(len(data["company_overview"]), 10)
        self.assertEqual(len(data["daily_prices"]), 1350)
        self.assertEqual(len(data["stock_news"]), manifest["expectedRows"]["stock_news"])
        self.assertGreater(len(data["stock_news"]), 0)
        report_counts = Counter(row["ticker"] for row in data["investment_reports"])
        self.assertEqual(len(data["investment_reports"]), 50)
        self.assertEqual(set(report_counts), set(manifest["tickers"]))
        self.assertEqual(set(report_counts.values()), {5})
        price_counts = Counter(row["symbol"] for row in data["daily_prices"])
        self.assertEqual(set(price_counts), set(manifest["tickers"]))
        self.assertEqual(set(price_counts.values()), {135})
        self.assertEqual(manifest["targetCoverage"]["priceStart"], "2026-01-02")
        self.assertEqual(manifest["targetCoverage"]["priceEnd"], "2026-07-17")

    def test_draft_fixture_is_rejected_without_explicit_opt_in(self):
        with self.assertRaisesRegex(DatasetValidationError, "draft dataset"):
            load_fixture(FIXTURE_DIR)

    def test_committed_news_is_compact_ytd_headline_metadata(self):
        manifest, data = load_fixture(FIXTURE_DIR, allow_draft=True)
        rows = data["stock_news"]
        counts = Counter(row["symbol"] for row in rows)

        self.assertEqual(manifest["datasetVersion"], "v1-draft.6")
        self.assertEqual(len(rows), 200)
        self.assertEqual(set(counts), set(manifest["tickers"]))
        self.assertEqual(set(counts.values()), {20})
        self.assertTrue(all(row["summary"] == "" for row in rows))
        self.assertTrue(all(row["source"] and row["headline"] and row["url"] for row in rows))
        self.assertTrue(
            all(_headline_mentions_ticker(row["symbol"], row["headline"]) for row in rows)
        )
        self.assertTrue(
            all(
                date(2026, 1, 2) <= date.fromisoformat(row["trade_date"]) <= date(2026, 7, 17)
                for row in rows
            )
        )

        id_keys = {(row["finnhub_id"], row["symbol"]) for row in rows}
        headline_keys = {
            (
                row["symbol"],
                re.sub(
                    r"\s+",
                    " ",
                    re.sub(r"[^a-z0-9\s]", "", row["headline"].casefold()),
                ).strip(),
            )
            for row in rows
        }
        self.assertEqual(len(id_keys), len(rows))
        self.assertEqual(len(headline_keys), len(rows))

        for ticker in manifest["tickers"]:
            ticker_rows = [row for row in rows if row["symbol"] == ticker]
            for anchor in DEFAULT_REPORT_DATES:
                window_start = anchor - timedelta(days=6)
                in_window = [
                    row
                    for row in ticker_rows
                    if window_start <= date.fromisoformat(row["trade_date"]) <= anchor
                ]
                self.assertLessEqual(len(in_window), 2)
            self.assertEqual(
                len(
                    [
                        row
                        for row in ticker_rows
                        if date.fromisoformat(row["trade_date"]) >= date(2026, 4, 1)
                    ]
                ),
                6,
            )

    def test_manifest_row_counts_must_match_fixture_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            copied_fixture = Path(temp_dir) / "v1"
            shutil.copytree(FIXTURE_DIR, copied_fixture)
            overview_path = copied_fixture / "company_overview.json"
            overview_path.write_text(json.dumps([{"symbol": "AAPL"}]), encoding="utf-8")

            with self.assertRaisesRegex(DatasetValidationError, "expected 10 rows"):
                load_fixture(copied_fixture, allow_draft=True)

    def _fixture_with_report(self, mutate=None):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        copied_fixture = Path(temp_dir.name) / "v1"
        shutil.copytree(FIXTURE_DIR, copied_fixture)
        manifest_path = copied_fixture / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        report = {
            "report_schema_version": 2,
            "ticker": "AAPL",
            "analysis_as_of": "2026-06-30T20:00:00+00:00",
            "generated_at": "2026-07-21T12:30:00+00:00",
            "generation_mode": "historical_backfill",
            "model_tier": "N",
            "model_provider": "deepseek",
            "model_name": "deepseek-v4-pro",
            "prompt_version": "market-analyst/2.0.1",
            "conclusion": "BUY",
            "conviction_level": "Medium",
            "target_price": 318.296,
            "upside_downside_pct": "+10.0%",
            "risk_level": "Medium",
            "reasoning": "The frozen fundamentals and price snapshot support the stated rating.",
            "full_report": "\n".join(
                (
                    "# Executive Summary",
                    "Analysis As Of: 2026-06-30",
                    "A sample-only conclusion based on the frozen snapshot.",
                    "## Business Moat and Catalysts",
                    "Business evidence is limited to the supplied snapshot.",
                    "## Financial and Valuation Analysis",
                    "Financial evidence and valuation are assessed together.",
                    "## Bull, Base, and Bear Scenarios",
                    "Bull, base, and bear cases use only frozen inputs.",
                    "## Risk Assessment",
                    "Risk remains medium.",
                    "## Data Limitations",
                    "No frozen news is available.",
                )
            ),
            "raw_financial_data": {
                "company_identity": {"symbol": "AAPL", "name": "Apple Inc."},
                "profitability_and_scale": {},
                "valuation_and_growth": {},
                "smart_money_consensus": {
                    "current_price": 289.36,
                    "analyst_target_price": 318.296,
                },
                "technical_and_momentum": {},
                "recent_catalysts": [],
                "snapshot_metadata": {
                    "schema_version": 2,
                    "price_as_of": "2026-06-30",
                    "look_ahead_protection": True,
                },
            },
            "agent_outputs": [{
                "run_id": "run-market-analyst-test",
                "agent_key": "market_analyst",
                "agent_version": "1.0.0",
                "output_schema_version": 1,
                "status": "completed",
                "output": {
                    "stance": "BUY",
                    "confidence": "Medium",
                    "summary": "Frozen evidence supports the rating.",
                    "evidence_refs": ["price:AAPL:2026-06-30"],
                },
            }],
            "generation_metadata": {
                "schema_version": 2,
                "workflow_name": "equity_research",
                "workflow_version": "1.0.0",
                "final_run_id": "run-market-analyst-test",
                "provenance_status": "complete",
                "aggregate_usage": {
                    "calls": 1,
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "by_model": [{
                        "provider": "deepseek",
                        "model": "deepseek-v4-pro",
                        "calls": 1,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "total_tokens": 150,
                    }],
                },
                "agent_runs": [{
                    "run_id": "run-market-analyst-test",
                    "agent_key": "market_analyst",
                    "agent_version": "1.0.0",
                    "sequence": 1,
                    "depends_on": [],
                    "provider": "deepseek",
                    "tier": "normal",
                    "requested_model": "deepseek-v4-pro",
                    "response_model": "deepseek-v4-pro",
                    "system_fingerprint": None,
                    "local_model_digest": None,
                    "prompt_version": "market-analyst/2.0.1",
                    "temperature": 0.1,
                    "response_format": "json",
                    "finish_reason": "stop",
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "total_tokens": 150,
                    },
                }],
            },
        }
        if mutate:
            mutate(report)
        report_path = copied_fixture / "investment_reports.json"
        report_path.write_text(json.dumps([report]), encoding="utf-8")
        manifest["expectedRows"]["investment_reports"] = 1
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return copied_fixture

    def test_complete_frozen_report_is_accepted(self):
        fixture = self._fixture_with_report()
        _, data = load_fixture(fixture, allow_draft=True)
        self.assertEqual(len(data["investment_reports"]), 1)

    def test_report_analysis_after_data_as_of_is_rejected(self):
        fixture = self._fixture_with_report(
            lambda report: report.update(analysis_as_of="2026-07-18T00:00:00+00:00")
        )
        with self.assertRaisesRegex(DatasetValidationError, "outside the frozen range"):
            load_fixture(fixture, allow_draft=True)

    def test_report_with_inconsistent_upside_is_rejected(self):
        fixture = self._fixture_with_report(
            lambda report: report.update(upside_downside_pct="+48%")
        )
        with self.assertRaisesRegex(DatasetValidationError, "does not match its target"):
            load_fixture(fixture, allow_draft=True)

    def test_report_with_unfrozen_news_is_rejected(self):
        def add_catalyst(report):
            report["raw_financial_data"]["recent_catalysts"] = [
                {"headline": "Not present in stock_news.json"}
            ]

        fixture = self._fixture_with_report(add_catalyst)
        with self.assertRaisesRegex(DatasetValidationError, "news absent"):
            load_fixture(fixture, allow_draft=True)

    def test_report_with_conflicting_embedded_date_is_rejected(self):
        def add_conflicting_date(report):
            report["full_report"] += "\n\nAnalysis As Of: 2023-10-15"

        fixture = self._fixture_with_report(add_conflicting_date)
        with self.assertRaisesRegex(DatasetValidationError, "conflicting analysis date"):
            load_fixture(fixture, allow_draft=True)

    def test_report_without_news_must_disclose_the_gap(self):
        def remove_news_disclosure(report):
            report["full_report"] = report["full_report"].replace(
                "No frozen news is available.",
                "Some inputs are limited.",
            )

        fixture = self._fixture_with_report(remove_news_disclosure)
        with self.assertRaisesRegex(DatasetValidationError, "disclose.*frozen news"):
            load_fixture(fixture, allow_draft=True)


if __name__ == "__main__":
    unittest.main()
