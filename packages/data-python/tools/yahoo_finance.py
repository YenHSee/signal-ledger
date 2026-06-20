import yfinance as yf

def get_daily_prices(symbol: str, period="1mo"):
    """
    通过 yfinance 获取股票的每日历史价格。
    """
    symbol = symbol.upper() # 养成好习惯：无论传进来什么，都转成大写
    print(f"📈 正在通过 yfinance 获取 {symbol} 的历史股价 (周期: {period})...")
    
    try:
        ticker = yf.Ticker(symbol)
        
        # 🌟 关键修复 1：强制关闭自动复权，这样才能同时拿到 Close 和 Adj Close
        hist = ticker.history(period=period, auto_adjust=False)
        
        if hist.empty:
            print(f"⚠️ 未能获取到 {symbol} 的价格数据，请检查股票代码是否正确。")
            return None

        prices_list = []
        
        for date, row in hist.iterrows():
            prices_list.append({
                "symbol": symbol,  # 🌟 关键修复 2：手动把股票代码塞进字典！
                "trade_date": date.strftime("%Y-%m-%d"),
                "open_price": round(float(row["Open"]), 4),
                "high_price": round(float(row["High"]), 4),
                "low_price": round(float(row["Low"]), 4),
                "close_price": round(float(row["Close"]), 4),
                "adjusted_close": round(float(row["Adj Close"]), 4), # 🌟 获取独立的复权价
                "volume": int(row["Volume"])
            })
            
        print(f"✅ 成功获取 {len(prices_list)} 天的 {symbol} 股价数据！")
        return prices_list

    except Exception as e:
        print(f"❌ 获取股价失败: {e}")
        return None

if __name__ == "__main__":
    data = get_daily_prices("NVDA", period="1mo")
    
    if data:
        print("最新一天的完整数据展示:")
        print(data[-1])