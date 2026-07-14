import os
import sys
import time
import yfinance as yf

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cache_manager import load_from_kv_cache, save_to_kv_cache

def get_company_overview(ticker: str):
    ticker = ticker.upper()
    
    # Check the optional Cloudflare KV cache first.
    cached_data = load_from_kv_cache(ticker)
    
    # A valid Yahoo Finance profile normally includes a business summary.
    if cached_data and "longBusinessSummary" in cached_data:
        print(f"⚡ [Cache hit] Using cached fundamentals for {ticker}")
        return cached_data

    print(f"🌐 [API request] Fetching {ticker} fundamentals from Yahoo Finance...")
    
    try:
        yf_stock = yf.Ticker(ticker)
        
        # .info contains the company profile, valuation, and financial metrics.
        overview_data = yf_stock.info

        # Unknown symbols can produce a small, incomplete dictionary.
        if not overview_data or "symbol" not in overview_data or len(overview_data) < 10:
            print(f"⚠️ [API warning] Yahoo Finance returned no valid fundamentals for {ticker}")
            return None
        
        time.sleep(1.5)
        save_to_kv_cache(ticker, overview_data)
        print(f"💾 [Cache] Saved fundamentals for {ticker}")
        
        return overview_data

    except Exception as e:
        print(f"❌ [Network error] Failed to fetch fundamentals for {ticker}: {e}")
        return None
    
    
def get_daily_prices(tickers: list, period="1mo"):
    print(f"📥 Downloading price history for {len(tickers)} symbols (period: {period})...")
    
    try:
        df = yf.download(tickers, period=period, auto_adjust=False, group_by='ticker', progress=True)
        
        if df.empty:
            print("⚠️ The batch download returned no data.")
            return None
            
        print("✅ Price history download completed.")
        return df

    except Exception as e:
        print(f"❌ Failed to download price history: {e}")
        return None

if __name__ == "__main__":
    data = get_daily_prices("NVDA", period="1mo")
    
    if data:
        print("Latest available row:")
        print(data[-1])
