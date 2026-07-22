import sys
import unittest
from datetime import date
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from tools.sec_financials import (  # noqa: E402
    build_sec_snapshots,
    latest_fact_value,
    select_sec_snapshot,
)


class SecFinancialSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.submissions = {
            "cik": "320193",
            "filings": {
                "recent": {
                    "accessionNumber": ["annual", "quarter", "future", "event"],
                    "filingDate": ["2025-10-31", "2026-02-01", "2026-08-01", "2026-01-05"],
                    "reportDate": ["2025-09-27", "2025-12-27", "2026-06-27", "2026-01-05"],
                    "acceptanceDateTime": [None, None, None, None],
                    "form": ["10-K", "10-Q", "10-Q", "8-K"],
                    "primaryDocument": ["annual.htm", "quarter.htm", "future.htm", "event.htm"],
                }
            },
        }
        self.companyfacts = {
            "cik": 320193,
            "entityName": "Apple Inc.",
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "label": "Assets",
                        "units": {
                            "USD": [
                                {"accn": "annual", "form": "10-K", "filed": "2025-10-31", "end": "2025-09-27", "val": 100},
                                {"accn": "quarter", "form": "10-Q", "filed": "2026-02-01", "end": "2025-12-27", "val": 110},
                                {"accn": "future", "form": "10-Q", "filed": "2026-08-01", "end": "2026-06-27", "val": 120},
                            ]
                        },
                    }
                }
            },
        }

    def test_build_and_select_are_point_in_time(self):
        result = build_sec_snapshots(
            "AAPL",
            date(2026, 7, 17),
            earliest_as_of=date(2026, 1, 9),
            submissions=self.submissions,
            companyfacts=self.companyfacts,
        )
        report_input = {"sec_snapshots": result["snapshots"]}
        january = select_sec_snapshot(report_input, date(2026, 1, 9))
        july = select_sec_snapshot(report_input, date(2026, 7, 17))
        annual = select_sec_snapshot(report_input, date(2026, 7, 17), {"10-K"})

        self.assertEqual(january["filing"]["accession"], "annual")
        self.assertEqual(july["filing"]["accession"], "quarter")
        self.assertEqual(annual["filing"]["accession"], "annual")
        self.assertEqual(latest_fact_value(july, "total_assets"), 110.0)
        self.assertNotIn("future", {row["filing"]["accession"] for row in result["snapshots"]})


if __name__ == "__main__":
    unittest.main()
