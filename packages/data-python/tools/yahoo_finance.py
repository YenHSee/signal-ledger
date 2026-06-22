import os
import sys
import yfinance as yf

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cache_manager import save_to_cache, load_from_cache

def get_company_overview(ticker: str):
    """
    通过 yfinance 获取公司基本面数据 (冷数据)。
    自带 7 天缓存机制，防止频繁请求被 Yahoo 封 IP。
    """
    ticker = ticker.upper()
    
    # 1. 检查缓存
    cached_data = load_from_cache(ticker, max_age_days=7)
    
    # 🌟 严谨校验：雅虎的数据里通常会有 longBusinessSummary(公司简介) 或 trailingPE
    if cached_data and "longBusinessSummary" in cached_data:
        print(f"⚡ [缓存命中] 正在使用本地基本面数据: {ticker}")
        return cached_data

    print(f"🌐 [API 请求] 正在向 Yahoo Finance 获取 {ticker} 的基本面数据...")
    
    try:
        # 2. 发起真实的 API 请求
        yf_stock = yf.Ticker(ticker)
        
        # .info 是 yfinance 获取基本面（财报、市盈率、简介等）的核心属性
        overview_data = yf_stock.info

        # 3. 校验数据是否有效 (雅虎如果查不到股票，可能会返回一个只有寥寥几个键的废字典)
        if not overview_data or "symbol" not in overview_data or len(overview_data) < 10:
            print(f"⚠️ [API 警告] Yahoo Finance 未返回有效的基本面数据: {ticker}")
            return None
        
        # 4. 存入缓存并返回
        save_to_cache(ticker, overview_data)
        print(f"💾 [数据持久化] 基本面数据已保存至缓存: {ticker}")
        
        return overview_data

    except Exception as e:
        print(f"❌ [网络错误] 获取 {ticker} 基本面失败: {e}")
        return None
    
    
def get_daily_prices(ticker: str, period="1mo"):
    """
    通过 yfinance 获取股票的每日历史价格。
    """
    # 1. 这里的 ticker 永远是纯文本字符串 "NVDA"
    ticker = ticker.upper() 
    print(f"📈 正在通过 yfinance 获取 {ticker} 的历史股价 (周期: {period})...")
    
    try:
        # 🌟 修复关键：起个新名字叫 yf_stock，千万不要覆盖原来的 ticker！
        yf_stock = yf.Ticker(ticker) 
        
        # 使用 yf_stock 去获取数据
        hist = yf_stock.history(period=period, auto_adjust=False)
        
        if hist.empty:
            print(f"⚠️ 未能获取到 {ticker} 的价格数据，请检查股票代码是否正确。")
            return None

        prices_list = []
        
        for date, row in hist.iterrows():
            prices_list.append({
                "symbol": ticker, 
                "trade_date": date.strftime("%Y-%m-%d"),
                "open_price": round(float(row["Open"]), 4),
                "high_price": round(float(row["High"]), 4),
                "low_price": round(float(row["Low"]), 4),
                "close_price": round(float(row["Close"]), 4),
                "adjusted_close": round(float(row["Adj Close"]), 4), 
                "volume": int(row["Volume"])
            })
            
        print(f"✅ 成功获取 {len(prices_list)} 天的 {ticker} 股价数据！")
        return prices_list

    except Exception as e:
        print(f"❌ 获取股价失败: {e}")
        return None

if __name__ == "__main__":
    data = get_daily_prices("NVDA", period="1mo")
    
    if data:
        print("最新一天的完整数据展示:")
        print(data[-1])

