"""Synchronize free SEC 10-K/10-Q snapshots into the live database."""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))
load_dotenv(PACKAGE_ROOT / ".env")

from db.connection import close_db_pool, init_db_pool
from db.repositories import upsert_sec_financial_snapshots
from db.schema import init_tables
from runtime_mode import assert_live_write_target
from tools.sec_financials import build_sec_snapshots


DEFAULT_TICKERS = (
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",
    "META", "TSLA", "AMD", "JPM", "WMT",
)


def sync_tickers(tickers: list[str], as_of: date) -> int:
    assert_live_write_target("synchronize SEC financial snapshots")
    init_tables()
    init_db_pool(min_conn=1, max_conn=2)
    total = 0
    try:
        for ticker in tickers:
            normalized = ticker.upper()
            result = build_sec_snapshots(normalized, as_of)
            written = upsert_sec_financial_snapshots(normalized, result["snapshots"])
            total += written
            print(f"{normalized}: synchronized {written} SEC snapshots")
    finally:
        close_db_pool()
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", nargs="+", default=list(DEFAULT_TICKERS))
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    total = sync_tickers(args.tickers, args.as_of)
    print(f"SEC snapshots synchronized: {total}")


if __name__ == "__main__":
    main()
