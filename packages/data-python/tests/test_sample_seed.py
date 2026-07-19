from collections import Counter
import json
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


FIXTURE_DIR = REPO_ROOT / "sample-data" / "v1"

class SampleFixtureTests(unittest.TestCase):
    def test_committed_draft_contains_fundamentals_and_one_year_of_prices(self):
        manifest, data = load_fixture(FIXTURE_DIR, allow_draft=True)

        self.assertEqual(manifest["status"], "draft")
        self.assertEqual(len(manifest["tickers"]), 10)
        self.assertEqual(len(data["company_overview"]), 10)
        self.assertEqual(len(data["daily_prices"]), 2510)
        self.assertFalse(data["stock_news"])
        self.assertFalse(data["investment_reports"])
        price_counts = Counter(row["symbol"] for row in data["daily_prices"])
        self.assertEqual(set(price_counts), set(manifest["tickers"]))
        self.assertEqual(set(price_counts.values()), {251})

    def test_draft_fixture_is_rejected_without_explicit_opt_in(self):
        with self.assertRaisesRegex(DatasetValidationError, "draft dataset"):
            load_fixture(FIXTURE_DIR)

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
            "ticker": "AAPL",
            "model_tier": "L",
            "conclusion": "BUY",
            "conviction_level": "Medium",
            "target_price": 318.296,
            "upside_downside_pct": "+10.0%",
            "risk_level": "Medium",
            "reasoning": "The frozen fundamentals and price snapshot support the stated rating.",
            "full_report": "\n".join(
                (
                    "# Executive Summary",
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
            },
            "generated_at": "2026-06-30T20:00:00+00:00",
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

    def test_report_after_data_as_of_is_rejected(self):
        fixture = self._fixture_with_report(
            lambda report: report.update(generated_at="2026-07-18T00:00:00+00:00")
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
            report["full_report"] += "\n\nGenerated At: 2023-10-15"

        fixture = self._fixture_with_report(add_conflicting_date)
        with self.assertRaisesRegex(DatasetValidationError, "conflicting generated date"):
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
