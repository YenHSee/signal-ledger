import os
import sys
import time
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

FINNHUB_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"

# Finnhub's free tier allows 60 calls per minute, so calls are paced globally.
_MIN_CALL_INTERVAL_SECONDS = 1.0
_last_call_at = 0.0


def _pace():
    """Ensure at least one second between Finnhub requests."""
    global _last_call_at
    elapsed = time.time() - _last_call_at
    if elapsed < _MIN_CALL_INTERVAL_SECONDS:
        time.sleep(_MIN_CALL_INTERVAL_SECONDS - elapsed)
    _last_call_at = time.time()


def get_company_news(symbol: str, from_date: str, to_date: str, max_retries: int = 2):
    """
    Fetch company news for a symbol in the inclusive date range.

    Dates use YYYY-MM-DD. Returns raw Finnhub dictionaries; after retries are
    exhausted, an empty list lets the caller skip the symbol safely.
    """
    api_key = config.FINNHUB_API_KEY
    if not api_key:
        print("⚠️ [Finnhub] FINNHUB_API_KEY is not configured; skipping news ingestion")
        return []

    symbol = symbol.upper()
    params = {"symbol": symbol, "from": from_date, "to": to_date, "token": api_key}

    for attempt in range(max_retries + 1):
        _pace()
        try:
            response = requests.get(FINNHUB_COMPANY_NEWS_URL, params=params, timeout=15)

            # Wait before retrying a rate-limited request.
            if response.status_code == 429:
                print(f"⚠️ [Finnhub] {symbol} was rate limited (429); retrying in 15 seconds...")
                time.sleep(15)
                continue

            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                print(f"⚠️ [Finnhub] {symbol} returned an unexpected response: {data}")
                return []

            return data

        except Exception as e:
            if attempt < max_retries:
                print(f"⚠️ [Finnhub] Request {attempt + 1} failed for {symbol}: {e}; retrying...")
                time.sleep(2)
            else:
                print(f"❌ [Finnhub] News fetch failed for {symbol}; skipping: {e}")

    return []


if __name__ == "__main__":
    from datetime import date, timedelta

    today = date.today()
    news = get_company_news("AAPL", (today - timedelta(days=3)).isoformat(), today.isoformat())
    print(f"✅ Fetched {len(news)} AAPL news items")
    for item in news[:3]:
        print(f"  - [{item.get('source')}] {item.get('headline')}")
