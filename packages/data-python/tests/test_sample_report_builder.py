import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from scripts.build_sample_reports import (  # noqa: E402
    ACTIVE_REPORT_DATES,
    ACTIVE_TICKERS,
    DEFAULT_SINGLE_REPORT_DATE,
    build_fixture_context,
    historical_report_output_path,
    normalize_report,
)
from core.news_relevance import headline_matches_ticker  # noqa: E402


FIXTURE_DIR = REPO_ROOT / "sample-data" / "v1"


class SampleReportBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json

        cls.overviews = json.loads((FIXTURE_DIR / "company_overview.json").read_text())
        cls.prices = json.loads((FIXTURE_DIR / "daily_prices.json").read_text())
        cls.news = json.loads((FIXTURE_DIR / "stock_news.json").read_text())
        cls.aapl_report_input = json.loads(
            (FIXTURE_DIR / "report_inputs" / "AAPL.json").read_text()
        )

    def test_context_uses_only_prices_and_news_available_as_of_date(self):
        as_of = date(2026, 1, 9)
        context = build_fixture_context("AAPL", as_of, self.overviews, self.prices, self.news)

        self.assertLessEqual(
            date.fromisoformat(context["smart_money_consensus"]["price_trade_date"]), as_of
        )
        self.assertTrue(
            all(date.fromisoformat(item["date"]) <= as_of for item in context["recent_catalysts"])
        )
        self.assertTrue(
            all(date.fromisoformat(item["date"]) <= as_of for item in context["recent_sec_filings"])
        )
        self.assertIsNone(context["valuation_and_growth"]["trailing_pe"])
        self.assertTrue(context["snapshot_metadata"]["look_ahead_protection"])
        self.assertEqual(context["snapshot_metadata"]["news_window_start"], "2025-12-10")
        self.assertTrue(
            all(
                headline_matches_ticker("AAPL", item["headline"])
                for item in context["recent_catalysts"]
            )
        )

    def test_default_schedule_has_eighteen_reports(self):
        tickers = {row["symbol"] for row in self.overviews}
        total = sum(
            len(ACTIVE_REPORT_DATES) if ticker in ACTIVE_TICKERS else 1
            for ticker in tickers
        )
        self.assertEqual(total, 50)
        self.assertEqual(DEFAULT_SINGLE_REPORT_DATE, date(2026, 7, 17))

    def test_historical_report_archive_filename_uses_analysis_date(self):
        path = historical_report_output_path(
            {
                "analysis_as_of": "2026-02-20T21:00:00+00:00",
                "ticker": "NVDA",
                "model_tier": "N",
            },
            Path("/tmp/reports"),
        )
        self.assertEqual(path.name, "2026-02-20_NVDA_N_report.json")

    def test_historical_input_provides_point_in_time_sec_and_long_price_history(self):
        as_of = date(2026, 1, 9)
        context = build_fixture_context(
            "AAPL",
            as_of,
            self.overviews,
            self.prices,
            self.news,
            report_input=self.aapl_report_input,
        )
        metadata = context["snapshot_metadata"]
        self.assertLessEqual(date.fromisoformat(metadata["fundamentals_filed_at"]), as_of)
        self.assertEqual(metadata["sec_accession"], "0000320193-25-000079")
        self.assertIsNotNone(context["technical_and_momentum"]["moving_averages"]["day_200_ma"])
        self.assertIsNotNone(context["valuation_and_growth"]["trailing_pe"])
        self.assertIsNotNone(context["balance_sheet_and_cash_flow"]["free_cash_flow"])
        self.assertEqual(
            context["profitability_and_scale"]["statement_metadata"]["period_end"],
            "2025-09-27",
        )
        self.assertEqual(
            context["balance_sheet_and_cash_flow"]["cash_flow_metadata"]["period_type"],
            "annual",
        )
        self.assertEqual(
            context["valuation_and_growth"]["trailing_pe_basis"]["method"],
            "price_divided_by_latest_filed_annual_diluted_eps",
        )

    def test_context_evaluates_the_immediately_previous_call(self):
        previous = {
            "report_schema_version": 2,
            "analysis_as_of": "2026-01-09T21:00:00+00:00",
            "conclusion": "BUY",
            "conviction_level": "Medium",
            "target_price": 275.0,
            "raw_financial_data": {
                "smart_money_consensus": {"current_price": 259.37}
            },
        }
        context = build_fixture_context(
            "AAPL",
            date(2026, 1, 23),
            self.overviews,
            self.prices,
            self.news,
            report_input=self.aapl_report_input,
            previous_report=previous,
        )
        review = context["previous_report"]
        self.assertEqual(review["analysis_as_of"], previous["analysis_as_of"])
        self.assertEqual(review["evaluation_as_of"], "2026-01-23")
        self.assertEqual(review["verdict_status"], "interim")
        self.assertEqual(review["days_elapsed"], 14)

    def test_normalizer_recomputes_upside_and_preserves_model_report(self):
        as_of = date(2026, 3, 31)
        context = build_fixture_context("AAPL", as_of, self.overviews, self.prices, self.news)
        model_report = """# Executive Summary

## Prior Call Review

No prior call exists.

## Business Moat and Catalysts

Frozen evidence only.

## Financial and Valuation Analysis

Unavailable.

## Bull, Base, and Bear Scenarios

Scenario analysis.

## Risk Assessment

Evidence risk.

## Data Limitations

Point-in-time fundamentals are unavailable.
"""
        generated = self._generated_envelope(
            context,
            as_of,
            conclusion="buy",
            conviction_level="medium",
            target_price="$250.00",
            upside_downside_pct="+999%",
            risk_level="HIGH",
            reasoning="Frozen evidence supports a cautious sample conclusion.",
            full_report=model_report,
        )
        report = normalize_report(
            "AAPL",
            as_of,
            context,
            generated,
        )

        expected = (report["target_price"] / context["smart_money_consensus"]["current_price"] - 1) * 100
        self.assertEqual(report["upside_downside_pct"], f"{expected:+.1f}%")
        self.assertEqual(report["conclusion"], "BUY")
        self.assertEqual(report["full_report"], model_report.strip())

    def test_normalizer_rejects_invalid_target_instead_of_inventing_one(self):
        as_of = date(2026, 1, 9)
        context = build_fixture_context("AAPL", as_of, self.overviews, self.prices, self.news)
        with self.assertRaisesRegex(Exception, "invalid target price"):
            normalize_report(
                "AAPL",
                as_of,
                context,
                self._generated_envelope(
                    context,
                    as_of,
                    conclusion="HOLD",
                    conviction_level="Low",
                    target_price="unknown",
                    risk_level="High",
                    reasoning="Evidence is limited.",
                    full_report="Report body",
                ),
            )

    @staticmethod
    def _generated_envelope(context, as_of, **analysis):
        run_id = "run-market-analyst-test"
        return {
            "report_schema_version": 2,
            "ticker": "AAPL",
            "analysis_as_of": datetime.combine(
                as_of, datetime.min.time(), tzinfo=timezone.utc
            ).isoformat(),
            "generated_at": "2026-07-21T12:30:00+00:00",
            "generation_mode": "historical_backfill",
            "model_tier": "N",
            "model_provider": "deepseek",
            "model_name": "deepseek-v4-pro",
            "prompt_version": "market-analyst/2.0.1",
            "raw_financial_data": context,
            "agent_outputs": [{
                "run_id": run_id,
                "output": {"stance": analysis["conclusion"], "confidence": "Medium"},
            }],
            "generation_metadata": {
                "final_run_id": run_id,
                "agent_runs": [{"run_id": run_id}],
            },
            **analysis,
        }


if __name__ == "__main__":
    unittest.main()
