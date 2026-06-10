import requests
from config import Config
from core.cache_manager import save_to_cache, load_from_cache

def get_stock_data(ticker: str):
    cached_data = load_from_cache(ticker)
    if cached_data:
        print(f"⚡ [缓存命中] 正在使用本地数据: {ticker}")
        return cached_data

    print(f"🌐 [API 请求] 正在从 Alpha Vantage 获取: {ticker}")
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={Config.ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "Note" not in data and "Error Message" not in data:
        save_to_cache(ticker, data)
        print(f"💾 [数据持久化] 已保存: {ticker}")
    else:
        print(f"⚠️ [API 警告] 请求异常，未缓存数据: {data}")

    return data