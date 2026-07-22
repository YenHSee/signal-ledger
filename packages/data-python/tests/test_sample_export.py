import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from scripts.export_sample_data import (  # noqa: E402
    SampleExportError,
    _json_value,
    validate_prices,
)


class SampleExportTests(unittest.TestCase):
    def _rows(self, ticker: str, count: int = 135) -> list[dict]:
        start = date(2026, 1, 2)
        end = date(2026, 7, 17)
        span_days = (end - start).days
        rows = []
        for offset in range(count):
            trade_date = start + timedelta(days=round(offset * span_days / (count - 1)))
            rows.append(
                {
                    "symbol": ticker,
                    "trade_date": trade_date.isoformat(),
                    "close_price": 100.0,
                    "volume": 1_000,
                }
            )
        return rows

    def test_non_finite_numbers_become_json_null(self):
        self.assertIsNone(_json_value(float("nan")))
        self.assertIsNone(_json_value(float("inf")))

    def test_duplicate_symbol_date_is_rejected(self):
        rows = self._rows("AAPL")
        rows.append(dict(rows[0]))
        with self.assertRaisesRegex(SampleExportError, "duplicate"):
            validate_prices(rows, ["AAPL"], date(2026, 1, 2), date(2026, 7, 17))

    def test_missing_ticker_is_rejected(self):
        with self.assertRaisesRegex(SampleExportError, "MSFT"):
            validate_prices(
                self._rows("AAPL"),
                ["AAPL", "MSFT"],
                date(2026, 1, 2),
                date(2026, 7, 17),
            )


if __name__ == "__main__":
    unittest.main()
