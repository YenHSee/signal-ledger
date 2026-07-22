import sys
import unittest
from datetime import date
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from core.previous_call import (  # noqa: E402
    build_previous_call_review,
    classify_previous_call,
)


class PreviousCallTests(unittest.TestCase):
    def test_directional_and_hold_verdicts(self):
        self.assertEqual(classify_previous_call("BUY", 2.0), "FAVORABLE")
        self.assertEqual(classify_previous_call("BUY", -2.0), "ADVERSE")
        self.assertEqual(classify_previous_call("SELL", -3.0), "FAVORABLE")
        self.assertEqual(classify_previous_call("SELL", 1.0), "FLAT")
        self.assertEqual(classify_previous_call("HOLD", 4.9), "STABLE")
        self.assertEqual(classify_previous_call("HOLD", 5.1), "UPSIDE_BREAKOUT")
        self.assertEqual(classify_previous_call("HOLD", -5.1), "DOWNSIDE_BREAKDOWN")

    def test_review_records_reproducible_prices_and_horizon(self):
        review = build_previous_call_review(
            {
                "report_schema_version": 2,
                "analysis_as_of": "2026-01-09T21:00:00+00:00",
                "conclusion": "BUY",
                "conviction_level": "Medium",
                "target_price": 275.0,
                "raw_financial_data": {
                    "smart_money_consensus": {"current_price": 250.0}
                },
            },
            evaluation_as_of=date(2026, 1, 30),
            evaluation_price=260.0,
        )
        self.assertEqual(review["days_elapsed"], 21)
        self.assertEqual(review["performance_since_pct"], 4.0)
        self.assertEqual(review["verdict"], "FAVORABLE")
        self.assertEqual(review["verdict_status"], "interim")


if __name__ == "__main__":
    unittest.main()
