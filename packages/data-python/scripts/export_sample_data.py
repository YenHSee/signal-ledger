"""Build frozen fundamentals and price fixtures without mutating the live database."""

import argparse
import json
import math
import os
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from runtime_mode import assert_live_read_source
from scripts.seed_sample_data import load_fixture


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_DIR = REPO_ROOT / "sample-data" / "v1"
DEFAULT_PRICE_START = date(2026, 1, 2)
DEFAULT_PRICE_END = date(2026, 7, 17)
DATASET_VERSION = "v1-draft.5"


class SampleExportError(RuntimeError):
    """Raised when source data cannot produce a complete, deterministic fixture."""


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        return _json_value(value.item())
    raise SampleExportError(f"Unsupported fixture value type: {type(value).__name__}")

def _price_value(value: Any) -> float | None:
    normalized = _json_value(value)
    return round(float(normalized), 4) if normalized is not None else None


def _volume_value(value: Any) -> int | None:
    normalized = _json_value(value)
    return int(round(float(normalized))) if normalized is not None else None



def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _load_manifest(fixture_dir: Path) -> dict:
    try:
        manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SampleExportError(f"Cannot read the sample manifest: {error}") from error
    tickers = manifest.get("tickers")
    if not isinstance(tickers, list) or len(tickers) != 10 or len(set(tickers)) != 10:
        raise SampleExportError("The v1 exporter requires exactly 10 unique manifest tickers.")
    return manifest


def export_fundamentals(tickers: list[str]) -> list[dict]:
    import psycopg2
    from config import config
    from psycopg2.extras import RealDictCursor

    assert_live_read_source("export sample fundamentals")
    connection = psycopg2.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
    )
    try:
        connection.set_session(readonly=True, autocommit=False)
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM company_overview WHERE symbol = ANY(%s) ORDER BY symbol",
                (tickers,),
            )
            rows = [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()

    found = {row["symbol"] for row in rows}
    missing = sorted(set(tickers) - found)
    if missing or len(rows) != len(tickers):
        raise SampleExportError(f"Missing or duplicate fundamentals for: {missing}.")
    return [{key: _json_value(value) for key, value in row.items()} for row in rows]


def _frame_for_ticker(frame, ticker: str):
    if getattr(frame.columns, "nlevels", 1) == 1:
        return frame
    level_values = [set(frame.columns.get_level_values(level)) for level in range(frame.columns.nlevels)]
    for level, values in enumerate(level_values):
        if ticker in values:
            return frame.xs(ticker, axis=1, level=level)
    raise SampleExportError(f"Cannot locate {ticker} in the downloaded price columns.")


def download_prices(tickers: list[str], start: date, end: date) -> list[dict]:
    import yfinance as yf

    rows = []
    exclusive_end = end + timedelta(days=1)
    for ticker in tickers:
        frame = yf.download(
            ticker,
            start=start.isoformat(),
            end=exclusive_end.isoformat(),
            auto_adjust=False,
            actions=False,
            progress=False,
            threads=False,
        )
        if frame is None or frame.empty:
            raise SampleExportError(f"yfinance returned no prices for {ticker}.")
        frame = _frame_for_ticker(frame, ticker)
        for index, source_row in frame.iterrows():
            trade_date = index.date() if hasattr(index, "date") else date.fromisoformat(str(index)[:10])
            row = {
                "symbol": ticker,
                "trade_date": trade_date.isoformat(),
                "open_price": _price_value(source_row.get("Open")),
                "high_price": _price_value(source_row.get("High")),
                "low_price": _price_value(source_row.get("Low")),
                "close_price": _price_value(source_row.get("Close")),
                "adjusted_close": _price_value(source_row.get("Adj Close", source_row.get("Close"))),
                "volume": _volume_value(source_row.get("Volume")),
            }
            rows.append(row)
    return sorted(rows, key=lambda row: (row["symbol"], row["trade_date"]))


def validate_prices(rows: list[dict], tickers: list[str], start: date, end: date) -> dict[str, int]:
    keys = [(row.get("symbol"), row.get("trade_date")) for row in rows]
    if len(keys) != len(set(keys)):
        raise SampleExportError("Downloaded prices contain duplicate symbol/date rows.")

    counts = {}
    for ticker in tickers:
        ticker_rows = [row for row in rows if row.get("symbol") == ticker]
        if not ticker_rows:
            raise SampleExportError(f"No frozen prices were produced for {ticker}.")
        dates = [date.fromisoformat(row["trade_date"]) for row in ticker_rows]
        if min(dates) < start or max(dates) > end:
            raise SampleExportError(f"{ticker} has a price outside the frozen date range.")
        if min(dates) > start + timedelta(days=7):
            raise SampleExportError(f"{ticker} does not cover the beginning of the date range.")
        if max(dates) < end - timedelta(days=7):
            raise SampleExportError(f"{ticker} does not cover the end of the date range.")
        if not 125 <= len(ticker_rows) <= 155:
            raise SampleExportError(f"{ticker} has an unexpected {len(ticker_rows)} daily rows.")
        for row in ticker_rows:
            if row["close_price"] is None or row["volume"] is None:
                raise SampleExportError(f"{ticker} contains an incomplete close or volume value.")
        counts[ticker] = len(ticker_rows)
    if set(symbol for symbol, _ in keys) != set(tickers):
        raise SampleExportError("Prices contain a symbol outside the manifest.")
    return counts


def align_overview_quotes(fundamentals: list[dict], prices: list[dict]) -> None:
    latest = {}
    for row in prices:
        latest[row["symbol"]] = row
    for overview in fundamentals:
        price = latest[overview["symbol"]]
        overview["current_price"] = price["close_price"]
        overview["price_as_of"] = f"{price['trade_date']}T00:00:00+00:00"


def build_fixture(
    fixture_dir: Path,
    start: date = DEFAULT_PRICE_START,
    end: date = DEFAULT_PRICE_END,
    dry_run: bool = False,
) -> dict:
    if end <= start:
        raise SampleExportError("price end must be after price start.")
    assert_live_read_source("build frozen sample data")
    fixture_dir = fixture_dir.resolve()
    manifest = _load_manifest(fixture_dir)
    tickers = manifest["tickers"]

    fundamentals = export_fundamentals(tickers)
    prices = download_prices(tickers, start, end)
    price_counts = validate_prices(prices, tickers, start, end)
    align_overview_quotes(fundamentals, prices)

    manifest["datasetVersion"] = DATASET_VERSION
    manifest["status"] = "draft"
    manifest["dataAsOf"] = end.isoformat()
    manifest["expectedRows"]["company_overview"] = len(fundamentals)
    manifest["expectedRows"]["daily_prices"] = len(prices)
    manifest["targetCoverage"].update(
        {
            "dailyPriceMonths": 7,
            "priceStart": start.isoformat(),
            "priceEnd": end.isoformat(),
        }
    )
    manifest.setdefault("sources", {}).update(
        {
            "fundamentals": "signal_ledger live database snapshot",
            "dailyPrices": "Yahoo Finance via yfinance",
            "redistributionReview": "pending",
        }
    )

    if not dry_run:
        with tempfile.TemporaryDirectory(prefix="sample-v1-", dir=fixture_dir.parent) as temp_name:
            temp_dir = Path(temp_name)
            _write_json(temp_dir / "company_overview.json", fundamentals)
            _write_json(temp_dir / "daily_prices.json", prices)
            _write_json(temp_dir / "manifest.json", manifest)
            for table in ("stock_news", "investment_reports"):
                shutil.copy2(fixture_dir / manifest["files"][table], temp_dir / manifest["files"][table])
            load_fixture(temp_dir, allow_draft=True)
            for filename in ("company_overview.json", "daily_prices.json", "manifest.json"):
                os.replace(temp_dir / filename, fixture_dir / filename)

    return {
        "datasetVersion": manifest["datasetVersion"],
        "dataAsOf": manifest["dataAsOf"],
        "fundamentals": len(fundamentals),
        "prices": len(prices),
        "priceCounts": price_counts,
        "dryRun": dry_run,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--price-start", type=date.fromisoformat, default=DEFAULT_PRICE_START)
    parser.add_argument("--price-end", type=date.fromisoformat, default=DEFAULT_PRICE_END)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_fixture(args.fixture_dir, args.price_start, args.price_end, args.dry_run)
    print(f"Dataset: {result['datasetVersion']} (draft)")
    print(f"Data as of: {result['dataAsOf']}")
    print(f"Fundamentals exported: {result['fundamentals']}")
    print(f"Daily prices exported: {result['prices']}")
    for ticker, count in sorted(result["priceCounts"].items()):
        print(f"  {ticker}: {count}")
    print("Dry run only; fixture files were not changed." if result["dryRun"] else "Fixture files updated atomically.")
    print("DRAFT ONLY — reports and redistribution review are still incomplete.")


if __name__ == "__main__":
    main()
