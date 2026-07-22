"""Freeze point-in-time price and SEC inputs used to generate historical reports."""

import argparse
import json
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import yfinance as yf


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from tools.sec_financials import build_sec_snapshots, sec_user_agent


DEFAULT_OUTPUT_DIR = REPO_ROOT / "sample-data" / "v1" / "report_inputs"
class ReportInputExportError(RuntimeError):
    pass


def _write_json_atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def _download_prices(
    ticker: str,
    as_of: date,
    earliest_as_of: date | None = None,
) -> list[dict]:
    start = (earliest_as_of or as_of) - timedelta(days=420)
    frame = yf.download(
        ticker,
        start=start.isoformat(),
        end=(as_of + timedelta(days=1)).isoformat(),
        auto_adjust=False,
        progress=False,
    )
    if frame.empty:
        raise ReportInputExportError(f"Yahoo Finance returned no prices for {ticker}.")
    rows = []
    for timestamp, row in frame.iterrows():
        def value(column):
            item = row[column]
            if hasattr(item, "iloc"):
                item = item.iloc[0]
            return None if item is None else float(item)

        rows.append({
            "trade_date": timestamp.date().isoformat(),
            "open_price": round(value("Open"), 4),
            "high_price": round(value("High"), 4),
            "low_price": round(value("Low"), 4),
            "close_price": round(value("Close"), 4),
            "adjusted_close": round(value("Adj Close"), 4),
            "volume": int(value("Volume")),
        })
    return rows


def export_report_input(
    ticker: str,
    as_of: date,
    output_dir: Path,
    earliest_as_of: date = date(2026, 1, 9),
) -> Path:
    ticker = ticker.upper()
    user_agent = sec_user_agent()
    sec_data = build_sec_snapshots(
        ticker,
        as_of,
        earliest_as_of=earliest_as_of,
        user_agent=user_agent,
    )
    payload = {
        "schema_version": 2,
        "ticker": ticker,
        "as_of": as_of.isoformat(),
        "prices": _download_prices(ticker, as_of, earliest_as_of),
        "sec_snapshots": sec_data["snapshots"],
        "recent_8k_events": sec_data["recent_8k_events"],
        "sources": {
            "prices": "Yahoo Finance via yfinance",
            "fundamentals": "SEC companyfacts 10-K/10-Q, filtered by accession and filing date",
            "filings": "SEC submissions JSON",
        },
    }
    output = output_dir.resolve() / f"{ticker}.json"
    _write_json_atomic(output, payload)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--earliest-as-of",
        type=date.fromisoformat,
        default=date(2026, 1, 9),
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    for ticker in args.ticker:
        output = export_report_input(
            ticker,
            args.as_of,
            args.output_dir,
            earliest_as_of=args.earliest_as_of,
        )
        print(f"Frozen report input: {output}")


if __name__ == "__main__":
    main()
