import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from scripts.export_sample_news import (  # noqa: E402
    SampleNewsExportError,
    _add_candidates,
    _load_checkpoint,
    balance_anomaly_dates,
    compute_anomaly_candidates,
    normalize_headline,
    rank_news_candidates,
)


def raw_news(
    news_id: int,
    headline: str,
    source: str = "Yahoo",
    related: str = "AAPL",
    day: int = 9,
    url: str | None = None,
) -> dict:
    timestamp = int(datetime(2026, 1, day, 12, tzinfo=timezone.utc).timestamp())
    return {
        "id": news_id,
        "datetime": timestamp,
        "headline": headline,
        "summary": "This summary must not be frozen.",
        "source": source,
        "related": related,
        "url": url if url is not None else f"https://example.com/{news_id}",
    }


class SampleNewsExportTests(unittest.TestCase):
    def test_ranking_prefers_direct_reputable_news_and_dedupes_headlines(self):
        rows = [
            raw_news(1, "Apple Same Story!", source="Benzinga", related="AAPL"),
            raw_news(2, "Apple same story", source="Reuters", related="AAPL"),
            raw_news(3, "Apple indirect story", source="Reuters", related="MSFT"),
            raw_news(4, "Direct Apple CNBC story", source="CNBC", related="AAPL"),
            raw_news(5, "Apple missing URL", source="Reuters", url=""),
            raw_news(6, "Generic market recap", source="Reuters", related="AAPL"),
        ]

        result = rank_news_candidates(
            "AAPL", rows, date(2026, 1, 3), date(2026, 1, 9)
        )

        self.assertEqual([row["finnhub_id"] for row in result], [2, 4])
        self.assertTrue(all(row["summary"] == "" for row in result))
        self.assertEqual(normalize_headline("Same Story!"), "same story")

    def test_anomaly_order_balances_months_before_filling_by_strength(self):
        rows = [
            {"trade_date": "2026-03-31", "close_price": 100, "volume": 100},
            {"trade_date": "2026-04-01", "close_price": 103, "volume": 100},
            {"trade_date": "2026-04-02", "close_price": 110, "volume": 100},
            {"trade_date": "2026-05-01", "close_price": 106, "volume": 100},
            {"trade_date": "2026-06-01", "close_price": 110, "volume": 100},
            {"trade_date": "2026-07-01", "close_price": 106, "volume": 100},
        ]
        candidates = compute_anomaly_candidates(rows)
        ordered = balance_anomaly_dates(candidates)

        self.assertEqual(
            [(item.year, item.month) for item in ordered[:4]],
            [(2026, 4), (2026, 5), (2026, 6), (2026, 7)],
        )

    def test_add_candidates_enforces_headline_and_id_deduplication(self):
        candidates = [
            {
                "finnhub_id": 1,
                "symbol": "AAPL",
                "headline": "First headline",
            },
            {
                "finnhub_id": 2,
                "symbol": "AAPL",
                "headline": "First Headline!",
            },
            {
                "finnhub_id": 3,
                "symbol": "AAPL",
                "headline": "Second headline",
            },
        ]
        selected = []
        added = _add_candidates(selected, candidates, set(), set(), limit=2)

        self.assertEqual(added, 2)
        self.assertEqual([row["finnhub_id"] for row in selected], [1, 3])

    def test_zero_limit_adds_nothing(self):
        selected = []
        added = _add_candidates(
            selected,
            [{"finnhub_id": 1, "symbol": "AAPL", "headline": "Headline"}],
            set(),
            set(),
            limit=0,
        )
        self.assertEqual(added, 0)
        self.assertEqual(selected, [])

    def test_mismatched_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "checkpoint.json"
            path.write_text(
                '{"schemaVersion": 1, "signature": {"start": "old"}, "requests": {}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SampleNewsExportError, "does not match"):
                _load_checkpoint(path, {"start": "new"})


if __name__ == "__main__":
    unittest.main()
