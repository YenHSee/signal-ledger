import requests
import yfinance as yf  # ⭐️ 引入免费的雅虎财经库
from config import config
from core.cache_manager import save_to_cache, load_from_cache

def get_stock_data(ticker: str):
    # 1. 检查缓存
    cached_data = load_from_cache(ticker)
    if cached_data:
        print(f"⚡ [缓存命中] 正在使用本地聚合数据: {ticker}")
        return cached_data

    print(f"🌐 [API 请求] 正在获取 {ticker} 的基本面与实时报价...")
    
    # 2. 获取冷数据：基本面 (Alpha Vantage - 省着用)
    overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={config.ALPHA_VANTAGE_API_KEY}"
    overview_data = requests.get(overview_url).json()

    if "Note" in overview_data or "Information" in overview_data or not overview_data:
        print(f"⚠️ [API 警告] Alpha Vantage 额度可能耗尽: {overview_data}")
        # 如果基本面拿不到，至少不要让程序死掉，给个空字典
        merged_data = {"Symbol": ticker} 
    else:
        merged_data = overview_data

    # 3. ⭐️ 获取热数据：实时报价 (用 yfinance，免费无限量！)
    try:
        print(f"📈 正在通过 Yahoo Finance 抓取 {ticker} 实时股价...")
        stock = yf.Ticker(ticker)
        # 提取最新一天的交易数据
        todays_data = stock.history(period='1d')
        
        if not todays_data.empty:
            current_price = round(todays_data['Close'].iloc[0], 2)
            open_price = todays_data['Open'].iloc[0]
            # 计算今日涨跌幅百分比
            change_percent = round(((current_price - open_price) / open_price) * 100, 2)
            
            merged_data["CurrentPrice"] = str(current_price)
            merged_data["ChangePercent"] = f"{change_percent}%"
        else:
            merged_data["CurrentPrice"] = "N/A"
            merged_data["ChangePercent"] = "N/A"
            
    except Exception as e:
        print(f"⚠️ [API 警告] 雅虎财经获取价格失败: {e}")
        merged_data["CurrentPrice"] = "N/A"
        merged_data["ChangePercent"] = "N/A"

    # 4. 存入当天的缓存
    save_to_cache(ticker, merged_data)
    print(f"💾 [数据持久化] 聚合数据已保存: {ticker}")

    return merged_data