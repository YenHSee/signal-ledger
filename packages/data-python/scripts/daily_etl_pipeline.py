import os
import sys
import time
import concurrent.futures

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
# Tools
from tools.wikipedia_scraper import get_sp500_tickers 
from tools.yahoo_finance import get_company_overview, get_daily_prices
from tools.finnhub_news import get_company_news
# Utils
from utils.data_transformer import transform_yfinance_overview_to_db, transform_yfinance_prices_to_db, transform_finnhub_news_to_db
# Database connections, schema management, and repositories
from db.connection import init_db_pool, close_db_pool
from db.schema import execute_simple_sql, init_tables
from db.repositories import insert_company_overview, insert_daily_prices, insert_stock_news, count_stock_news


def process_single_overview(ticker):
    """Synchronize fundamentals for one symbol in a worker thread."""
    try:
        raw_overview = get_company_overview(ticker)
        if raw_overview:
            clean_overview = transform_yfinance_overview_to_db(raw_overview)
            clean_overview["is_sp500"] = True 
            insert_company_overview(clean_overview)
    except Exception as e:
        print(f"⚠️ Skipping fundamentals for {ticker}: {e}")


def sync_company_news(tickers):
    """Incrementally ingest Finnhub news, with a 30-day first-run backfill."""
    from datetime import date, timedelta

    print(f"\n[STEP 5] 📰 Synchronizing company news for {len(tickers)} symbols (Finnhub)...")

    if not config.FINNHUB_API_KEY:
        print("⚠️ FINNHUB_API_KEY is not configured; skipping news ingestion.")
        return

    # Backfill 30 days for an empty table; otherwise fetch three days incrementally.
    lookback_days = 30 if count_stock_news() == 0 else 3
    today = date.today()
    from_date = (today - timedelta(days=lookback_days)).isoformat()
    to_date = today.isoformat()
    print(f"🗓️ Fetch window: {from_date} to {to_date} ({lookback_days} days)")

    total_inserted = 0
    success_count = 0
    for ticker in tickers:
        try:
            raw_news = get_company_news(ticker, from_date, to_date)
            if not raw_news:
                continue
            news_rows = transform_finnhub_news_to_db(ticker, raw_news)
            inserted = insert_stock_news(news_rows)
            total_inserted += inserted
            success_count += 1
        except Exception as e:
            print(f"⚠️ Skipping news for {ticker}: {e}")

    print(f"✅ News ingestion complete: {success_count} symbols had news; {total_inserted} rows inserted.")


def run_stock_pipeline():
    """Run the daily market-data ingestion pipeline."""
    
    print("\n" + "="*60)
    print("🚀 [START] Starting the S&P 500 ETL pipeline")
    print("="*60)

    # ---------------------------------------------------------
    # STEP 0: initialize the schema and database pool.
    # ---------------------------------------------------------
    print("\n[STEP 0] 🔧 Initializing the schema and database connection pool...")
    init_tables() 
    init_db_pool(min_conn=1, max_conn=20) 

    # ---------------------------------------------------------
    # STEP 1: fetch the constituent list.
    # ---------------------------------------------------------
    print("\n[STEP 1] 📋 Fetching the current S&P 500 constituent list...")
    tickers = get_sp500_tickers()
    if not tickers:
        print("❌ Unable to fetch the symbol list; stopping the pipeline.")
        close_db_pool() 
        return

    # ---------------------------------------------------------
    # STEP 2: reset constituent flags and refresh daily prices.
    # ---------------------------------------------------------
    print("\n[STEP 2] 🔄 Resetting constituent flags and clearing stale daily prices...")
    execute_simple_sql("UPDATE company_overview SET is_sp500 = FALSE;")
    execute_simple_sql("TRUNCATE TABLE daily_prices;")

    # ---------------------------------------------------------
    # STEP 3: synchronize company fundamentals concurrently.
    # ---------------------------------------------------------
    print(f"\n[STEP 3] 🏢 Synchronizing fundamentals for {len(tickers)} companies...")
    
    # Use 15 workers backed by the shared database pool.
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        executor.map(process_single_overview, tickers)

    print("✅ Fundamentals synchronization complete.")

    # ---------------------------------------------------------
    # STEP 4: download and bulk insert historical prices.
    # ---------------------------------------------------------
    print(f"\n[STEP 4] 📈 Downloading recent prices for {len(tickers)} symbols...")
    try:
        df = get_daily_prices(tickers, period="1mo")
        
        if df is not None:
            print("🔌 Writing price history through the shared connection pool...")
            success_count = 0
            for ticker in tickers:
                try:
                    ticker_df = df[ticker] if len(tickers) > 1 else df
                    ticker_df = ticker_df.dropna(subset=['Close'])
                    if ticker_df.empty:
                        continue
                    
                    raw_dict = ticker_df.to_dict(orient="index")
                    prices_list = transform_yfinance_prices_to_db(ticker, raw_dict)
                    
                    if prices_list and insert_daily_prices(prices_list):
                        success_count += 1
                        
                except Exception as single_err:
                    print(f"⚠️ Skipping malformed price data for {ticker}: {single_err}")
            
            print(f"✨ Persisted price history for {success_count} symbols.")
                
    except Exception as e:
        print(f"❌ Price download or bulk insert failed: {e}")

    # ---------------------------------------------------------
    # STEP 5: append new company news from Finnhub.
    # ---------------------------------------------------------
    sync_company_news(tickers)

    # ---------------------------------------------------------
    # Release database resources.
    # ---------------------------------------------------------
    close_db_pool()

    print("\n" + "="*60)
    print("🎉 [FINISH] Daily market data is ready.")
    print("="*60)


if __name__ == "__main__":
    start_time = time.time()
    run_stock_pipeline()
    print(f"\n⏱️ Total pipeline time: {round(time.time() - start_time, 2)} seconds")
