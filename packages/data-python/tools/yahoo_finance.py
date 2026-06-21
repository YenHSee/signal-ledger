import yfinance as yf

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