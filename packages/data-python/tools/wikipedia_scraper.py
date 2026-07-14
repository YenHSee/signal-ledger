import requests
import pandas as pd
import io

def get_sp500_tickers():
    """Fetch the current S&P 500 constituent list from Wikipedia."""
    print("🔍 Fetching the current S&P 500 constituent list from Wikipedia...")
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status() 
        
        html_buffer = io.StringIO(response.text)
        tables = pd.read_html(html_buffer)
        
        tickers = tables[0]['Symbol'].tolist()
        tickers = [str(ticker).replace('.', '-') for ticker in tickers]
        
        print(f"✅ Fetched {len(tickers)} symbols.")
        return tickers
        
    except Exception as e:
        print(f"❌ Failed to extract the S&P 500 table: {e}")
        return []
