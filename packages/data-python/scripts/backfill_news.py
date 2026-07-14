"""
One-time Finnhub news backfill.

The broad phase fetches one date range per symbol. Because Finnhub can truncate
busy symbols, the anomaly phase also fetches each large price-move or volume-spike
date individually. insert_stock_news deduplicates overlapping results by Finnhub ID.

Usage:
    python scripts/backfill_news.py                    # All S&P 500 symbols, 30 days
    python scripts/backfill_news.py --days 30 --tickers AAPL,MSFT
    python scripts/backfill_news.py --skip-broad       # Anomaly dates only
    python scripts/backfill_news.py --skip-anomaly     # Broad fetch only
"""

import argparse
import os
import sys
import time
from collections import defaultdict
from datetime import date, timedelta

import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from tools.finnhub_news import get_company_news
from utils.data_transformer import transform_finnhub_news_to_db
from db.schema import init_tables
from db.repositories import insert_stock_news

# Keep anomaly thresholds aligned with the frontend chart.
BIG_MOVE_PCT = 2.0
VOLUME_SPIKE_RATIO = 2.0
VOLUME_AVG_WINDOW = 30


def _connect():
    return psycopg2.connect(
        user=config.DB_USER, password=config.DB_PASSWORD,
        host=config.DB_HOST, port=config.DB_PORT, database=config.DB_NAME
    )


def get_backfill_symbols(connection):
    """Return S&P 500 symbols, falling back to symbols present in daily_prices."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT symbol FROM company_overview WHERE is_sp500 = TRUE ORDER BY symbol;")
        symbols = [row[0] for row in cursor.fetchall()]
        if symbols:
            return symbols
        cursor.execute("SELECT DISTINCT symbol FROM daily_prices ORDER BY symbol;")
        return [row[0] for row in cursor.fetchall()]


def load_price_rows(connection, from_date):
    """Load and group price rows in ascending date order."""
    grouped = defaultdict(list)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT symbol, trade_date, close_price, volume
            FROM daily_prices
            WHERE trade_date >= %s
            ORDER BY symbol, trade_date;
            """,
            (from_date,),
        )
        for symbol, trade_date, close_price, volume in cursor.fetchall():
            grouped[symbol].append({
                "date": trade_date,
                "close": float(close_price) if close_price is not None else None,
                "volume": int(volume) if volume is not None else None,
            })
    return grouped


def compute_anomaly_dates(price_rows):
    """
    Return dates with an absolute price move of at least 2%, or volume at least
    twice the rolling 30-day average.
    """
    anomaly_dates = []
    for index, row in enumerate(price_rows):
        prev = price_rows[index - 1] if index > 0 else None
        change_pct = None
        if prev and prev["close"] and row["close"] is not None:
            change_pct = (row["close"] - prev["close"]) / prev["close"] * 100

        volume_window = [
            r["volume"]
            for r in price_rows[max(0, index - (VOLUME_AVG_WINDOW - 1)):index + 1]
            if r["volume"] is not None
        ]
        avg_volume = sum(volume_window) / len(volume_window) if volume_window else None

        is_big_move = change_pct is not None and abs(change_pct) >= BIG_MOVE_PCT
        is_volume_spike = (
            row["volume"] is not None
            and avg_volume is not None
            and row["volume"] >= avg_volume * VOLUME_SPIKE_RATIO
        )

        if is_big_move or is_volume_spike:
            anomaly_dates.append(row["date"])
    return anomaly_dates


def fetch_and_store(symbol, from_date, to_date):
    """Fetch and store one date range; return (normalized rows, inserted rows)."""
    raw_news = get_company_news(symbol, from_date, to_date)
    if not raw_news:
        return 0, 0
    news_rows = transform_finnhub_news_to_db(symbol, raw_news)
    inserted = insert_stock_news(news_rows)
    return len(news_rows), inserted


def run_broad_backfill(symbols, from_date, to_date):
    print(f"\n[PHASE 1] 🌊 Broad fetch: {len(symbols)} symbols from {from_date} to {to_date}")
    total_inserted = 0
    for i, symbol in enumerate(symbols, 1):
        try:
            fetched, inserted = fetch_and_store(symbol, from_date, to_date)
            total_inserted += inserted
            print(f"  ({i}/{len(symbols)}) {symbol}: fetched {fetched}, inserted {inserted}")
        except Exception as e:
            print(f"  ⚠️ ({i}/{len(symbols)}) Broad fetch failed for {symbol}; skipping: {e}")
    print(f"✅ [PHASE 1] Complete: {total_inserted} rows inserted.")
    return total_inserted


def run_anomaly_backfill(connection, symbols, from_date):
    print("\n[PHASE 2] 🎯 Fetching news for detected anomaly dates...")
    prices_by_symbol = load_price_rows(connection, from_date)

    tasks = []  # (symbol, anomaly_date)
    for symbol in symbols:
        rows = prices_by_symbol.get(symbol)
        if not rows:
            continue
        for anomaly_date in compute_anomaly_dates(rows):
            tasks.append((symbol, anomaly_date))

    if not tasks:
        print("✅ [PHASE 2] No anomaly dates found in the selected window.")
        return 0

    est_minutes = len(tasks) / 60
    print(f"🗓️ Found {len(tasks)} symbol/date pairs; estimated time: {est_minutes:.0f} minutes")

    total_inserted = 0
    for i, (symbol, anomaly_date) in enumerate(tasks, 1):
        day = anomaly_date.isoformat()
        try:
            fetched, inserted = fetch_and_store(symbol, day, day)
            total_inserted += inserted
            print(f"  ({i}/{len(tasks)}) {symbol} @ {day}: fetched {fetched}, inserted {inserted}")
        except Exception as e:
            print(f"  ⚠️ ({i}/{len(tasks)}) Fetch failed for {symbol} @ {day}; skipping: {e}")
    print(f"✅ [PHASE 2] Complete: {total_inserted} rows inserted.")
    return total_inserted


def main():
    parser = argparse.ArgumentParser(description="One-time Finnhub news backfill")
    parser.add_argument("--days", type=int, default=30, help="Lookback days (default: 30)")
    parser.add_argument("--tickers", type=str, default=None,
                        help="Comma-separated symbols (default: all S&P 500 symbols)")
    parser.add_argument("--skip-broad", action="store_true", help="Skip the broad-fetch phase")
    parser.add_argument("--skip-anomaly", action="store_true", help="Skip the anomaly-date phase")
    args = parser.parse_args()

    if not config.FINNHUB_API_KEY:
        print("❌ FINNHUB_API_KEY is required. Add it to your .env file first.")
        sys.exit(1)

    start_time = time.time()
    today = date.today()
    from_date = today - timedelta(days=args.days)

    print("=" * 60)
    print(f"🚀 [START] News backfill ({args.days} days: {from_date} to {today})")
    print("=" * 60)

    # Ensure stock_news exists.
    init_tables()

    connection = _connect()
    try:
        if args.tickers:
            symbols = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        else:
            symbols = get_backfill_symbols(connection)

        if not symbols:
            print("❌ No symbols found in company_overview or daily_prices. Run the daily ETL first.")
            sys.exit(1)

        total = 0
        if not args.skip_broad:
            total += run_broad_backfill(symbols, from_date.isoformat(), today.isoformat())
        if not args.skip_anomaly:
            total += run_anomaly_backfill(connection, symbols, from_date)
    finally:
        connection.close()

    print("\n" + "=" * 60)
    print(f"🎉 [FINISH] Backfill complete: {total} rows inserted in {round(time.time() - start_time, 1)} seconds")
    print("=" * 60)


if __name__ == "__main__":
    main()
